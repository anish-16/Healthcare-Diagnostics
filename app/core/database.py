from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# PostgreSQL stores timestamptz in UTC; pinning the session timezone to UTC
# keeps returned datetimes consistently UTC regardless of server location.
connect_args = {}
if settings.database_url.startswith("postgresql"):
    connect_args["options"] = "-c timezone=UTC"

engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
