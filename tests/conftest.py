"""Test fixtures: isolated Postgres test DB, API client, and helpers."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("BCRYPT_ROUNDS", "4")  # fast hashing in tests only
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/eve_health_test",
)


def _ensure_database() -> None:
    admin_url = TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'eve_health_test'")
        ).scalar()
        if not exists:
            conn.execute(text("CREATE DATABASE eve_health_test"))
    admin_engine.dispose()


_ensure_database()

# Import the app only after pointing settings at the test DB.
os.environ["DATABASE_URL"] = TEST_DB_URL
from app.core.config import settings

settings.database_url = TEST_DB_URL
from app.core.database import Base

engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables(_database):
    """Delete rows between tests so tests are order-independent."""
    with engine.begin() as conn:
        for table in ("payments", "bookings", "centre_tests", "diagnostic_tests",
                      "diagnostic_centres", "users"):
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db_session():
    """A session for arranging data directly in tests."""
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


# ---------- helpers ----------

def register(client, email="patient@example.com", password="secret123", name="Test Patient"):
    return client.post("/api/auth/signup", json={
        "name": name, "email": email, "password": password,
    })


def auth_header(client, email="patient@example.com", password="secret123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user(client):
    register(client)
    headers = auth_header(client)
    return {"headers": headers}


@pytest.fixture
def catalogue(db_session):
    """One centre offering two tests at known prices."""
    from decimal import Decimal

    from app.models.models import CentreTest, DiagnosticCentre, DiagnosticTest

    centre = DiagnosticCentre(name="CityCare Diagnostics", location="MG Road, Pune")
    t1 = DiagnosticTest(name="CBC", description="Complete Blood Count")
    t2 = DiagnosticTest(name="Lipid Profile", description="Cholesterol panel")
    db_session.add_all([centre, t1, t2])
    db_session.flush()
    ct1 = CentreTest(centre_id=centre.id, test_id=t1.id, price=Decimal("299.00"))
    ct2 = CentreTest(centre_id=centre.id, test_id=t2.id, price=Decimal("899.00"))
    db_session.add_all([ct1, ct2])
    db_session.commit()
    return {"centre": centre, "tests": [t1, t2], "offerings": [ct1, ct2]}


@pytest.fixture
def booking(client, user, catalogue):
    """A future appointment booking for offering 0 (299.00)."""
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2027-03-01T10:00:00+05:30",
    })
    assert res.status_code == 201, res.text
    return res.json()
