"""Auth flow: signup, duplicate email, validation, login, protected endpoint."""

from tests.conftest import register


def test_signup_success(client):
    res = register(client)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "patient@example.com"
    assert "hashed_password" not in body and "password" not in body


def test_signup_duplicate_email(client):
    register(client)
    res = register(client, email="patient@example.com")
    assert res.status_code == 409
    assert res.json()["detail"] == "Email already registered"


def test_signup_invalid_email(client):
    res = register(client, email="not-an-email")
    assert res.status_code == 422


def test_signup_short_password(client):
    res = register(client, password="s1")
    assert res.status_code == 422


def test_signup_password_without_digit(client):
    res = register(client, password="onlyletters")
    assert res.status_code == 422


def test_login_success(client):
    register(client)
    res = client.post("/api/auth/login", json={
        "email": "patient@example.com", "password": "secret123",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_wrong_password(client):
    register(client)
    res = client.post("/api/auth/login", json={
        "email": "patient@example.com", "password": "wrongpass1",
    })
    assert res.status_code == 401


def test_login_unknown_email(client):
    res = client.post("/api/auth/login", json={
        "email": "ghost@example.com", "password": "whatever1",
    })
    assert res.status_code == 401


def test_me_without_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_with_garbled_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401


def test_me_success(client, user):
    res = client.get("/api/auth/me", headers=user["headers"])
    assert res.status_code == 200
    assert res.json()["email"] == "patient@example.com"
