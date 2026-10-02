"""Bookings: creation, server-side pricing, ownership, cancellation."""

from datetime import datetime, timezone

from tests.conftest import auth_header, register


def test_create_booking_success(client, user, catalogue):
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2027-03-01T10:00:00+05:30",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "PENDING"
    assert body["amount"] == "299.00"          # server-side price, exact decimal
    # 2027-03-01T10:00:00+05:30 normalized to UTC
    returned = datetime.fromisoformat(body["appointment_datetime"].replace("Z", "+00:00"))
    assert returned == datetime(2027, 3, 1, 4, 30, tzinfo=timezone.utc)


def test_booking_without_token(client, catalogue):
    res = client.post("/api/bookings", json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2027-03-01T10:00:00+00:00",
    })
    assert res.status_code == 401


def test_booking_invalid_centre_test_id(client, user):
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": 9999,
        "appointment_datetime": "2027-03-01T10:00:00+00:00",
    })
    assert res.status_code == 404


def test_booking_rejects_client_supplied_amount(client, user, catalogue):
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2027-03-01T10:00:00+00:00",
        "amount": 1.00,  # ignored by the schema
    })
    assert res.status_code == 201
    assert res.json()["amount"] == "299.00"


def test_booking_past_appointment_rejected(client, user, catalogue):
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2020-01-01T10:00:00+00:00",
    })
    assert res.status_code == 422


def test_booking_naive_datetime_rejected(client, user, catalogue):
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2027-03-01T10:00:00",  # no offset
    })
    assert res.status_code == 422


def test_list_bookings_returns_only_own(client, user, catalogue):
    client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][1].id,
        "appointment_datetime": "2027-04-02T09:00:00+00:00",
    })

    register(client, email="other@example.com", password="secret456", name="Other User")
    other_headers = auth_header(client, email="other@example.com", password="secret456")

    res = client.get("/api/bookings", headers=user["headers"])
    assert res.status_code == 200
    bookings = res.json()
    me = client.get("/api/auth/me", headers=user["headers"]).json()
    assert len(bookings) == 1
    assert bookings[0]["user_id"] == me["id"]

    other_res = client.get("/api/bookings", headers=other_headers)
    assert other_res.status_code == 200
    assert other_res.json() == []


def test_get_booking_of_other_user_forbidden(client, user, booking):
    register(client, email="other@example.com", password="secret456", name="Other User")
    other_headers = auth_header(client, email="other@example.com", password="secret456")

    res = client.get(f"/api/bookings/{booking['id']}", headers=other_headers)
    assert res.status_code == 403


def test_cancel_booking_of_other_user_forbidden(client, user, booking):
    register(client, email="other@example.com", password="secret456", name="Other User")
    other_headers = auth_header(client, email="other@example.com", password="secret456")

    res = client.patch(f"/api/bookings/{booking['id']}/cancel", headers=other_headers)
    assert res.status_code == 403


def test_get_missing_booking(client, user):
    res = client.get("/api/bookings/9999", headers=user["headers"])
    assert res.status_code == 404


def test_cancel_pending_booking(client, user, booking):
    res = client.patch(f"/api/bookings/{booking['id']}/cancel", headers=user["headers"])
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"


def test_cannot_cancel_twice(client, user, booking):
    client.patch(f"/api/bookings/{booking['id']}/cancel", headers=user["headers"])
    res = client.patch(f"/api/bookings/{booking['id']}/cancel", headers=user["headers"])
    assert res.status_code == 409


def test_booking_status_cannot_be_set_by_client(client, user, catalogue):
    # There is no endpoint that accepts a status field; sending one is ignored.
    res = client.post("/api/bookings", headers=user["headers"], json={
        "centre_test_id": catalogue["offerings"][0].id,
        "appointment_datetime": "2027-03-01T10:00:00+00:00",
        "status": "CONFIRMED",
    })
    assert res.status_code == 201
    assert res.json()["status"] == "PENDING"
