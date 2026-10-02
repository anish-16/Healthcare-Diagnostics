"""Payments and webhook: simulation outcomes, idempotency, state protection."""

from app.models.models import Payment
from tests.conftest import auth_header, register


def _webhook(event_id, booking_id, status="SUCCESS"):
    return {"event_id": event_id, "booking_id": booking_id, "status": status}


def test_successful_payment_confirms_booking(client, user, booking):
    res = client.post("/api/payments", headers=user["headers"], json={"booking_id": booking["id"]})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "SUCCESS"
    assert body["amount"] == booking["amount"]

    shown = client.get(f"/api/bookings/{booking['id']}", headers=user["headers"])
    assert shown.json()["status"] == "CONFIRMED"


def test_failed_payment_fails_booking(client, user, booking):
    res = client.post("/api/payments", headers=user["headers"],
                      json={"booking_id": booking["id"], "simulate": "failure"})
    assert res.status_code == 201
    assert res.json()["status"] == "FAILED"

    shown = client.get(f"/api/bookings/{booking['id']}", headers=user["headers"])
    assert shown.json()["status"] == "FAILED"


def test_payment_for_other_users_booking_forbidden(client, user, booking):
    register(client, email="other@example.com", password="secret456", name="Other User")
    other_headers = auth_header(client, email="other@example.com", password="secret456")
    res = client.post("/api/payments", headers=other_headers, json={"booking_id": booking["id"]})
    assert res.status_code in (403, 404)


def test_payment_missing_booking(client, user):
    res = client.post("/api/payments", headers=user["headers"], json={"booking_id": 9999})
    assert res.status_code == 404


def test_payment_without_token(client, booking):
    res = client.post("/api/payments", json={"booking_id": booking["id"]})
    assert res.status_code == 401


def test_duplicate_payment_prevented(client, user, booking):
    first = client.post("/api/payments", headers=user["headers"], json={"booking_id": booking["id"]})
    assert first.status_code == 201
    second = client.post("/api/payments", headers=user["headers"], json={"booking_id": booking["id"]})
    assert second.status_code == 409
    assert "already" in second.json()["detail"].lower()


def test_cancelled_booking_cannot_be_paid(client, user, booking):
    client.patch(f"/api/bookings/{booking['id']}/cancel", headers=user["headers"])
    res = client.post("/api/payments", headers=user["headers"], json={"booking_id": booking["id"]})
    assert res.status_code == 409


def test_list_and_get_own_payments(client, user, booking):
    client.post("/api/payments", headers=user["headers"], json={"booking_id": booking["id"]})

    res = client.get("/api/payments", headers=user["headers"])
    assert res.status_code == 200
    payments = res.json()
    assert len(payments) == 1
    payment_id = payments[0]["id"]

    shown = client.get(f"/api/payments/{payment_id}", headers=user["headers"])
    assert shown.status_code == 200
    assert shown.json()["booking_id"] == booking["id"]


def test_other_users_payment_hidden(client, user, booking):
    client.post("/api/payments", headers=user["headers"], json={"booking_id": booking["id"]})

    register(client, email="other@example.com", password="secret456", name="Other User")
    other_headers = auth_header(client, email="other@example.com", password="secret456")

    res = client.get("/api/payments", headers=other_headers)
    assert res.status_code == 200 and res.json() == []

    single = client.get("/api/payments/1", headers=other_headers)
    assert single.status_code == 404


def test_webhook_success_confirms_booking(client, db_session, user, booking):
    res = client.post("/api/payments/webhook", json=_webhook("evt_test_success_01", booking["id"]))
    assert res.status_code == 200
    ack = res.json()
    assert ack["received"] is True and ack["duplicate"] is False
    assert ack["payment_status"] == "SUCCESS"
    assert ack["booking_status"] == "CONFIRMED"

    payments = db_session.query(Payment).all()
    assert len(payments) == 1
    assert payments[0].amount is not None


def test_webhook_failure_fails_booking(client, user, booking):
    res = client.post("/api/payments/webhook", json=_webhook("evt_test_fail_01", booking["id"], "FAILED"))
    assert res.status_code == 200
    ack = res.json()
    assert ack["payment_status"] == "FAILED"
    assert ack["booking_status"] == "FAILED"


def test_webhook_nonexistent_booking(client):
    res = client.post("/api/payments/webhook", json=_webhook("evt_test_missing_01", 424242))
    assert res.status_code == 404


def test_webhook_malformed_payloads(client, booking):
    bad_payloads = [
        {"booking_id": booking["id"], "status": "SUCCESS"},                 # missing event_id
        {"event_id": "short", "booking_id": booking["id"], "status": "SUCCESS"},  # event_id too short
        {"event_id": "evt_valid_length_01", "status": "SUCCESS"},           # missing booking_id
        {"event_id": "evt_valid_length_01", "booking_id": booking["id"], "status": "WEIRD"},
        "not even a dict",
    ]
    for payload in bad_payloads:
        res = client.post("/api/payments/webhook", json=payload)
        assert res.status_code == 422, f"payload {payload!r} should fail validation"


def test_duplicate_webhook_delivery_is_idempotent(client, db_session, user, booking):
    event = _webhook("evt_test_dup_01", booking["id"], "SUCCESS")

    first = client.post("/api/payments/webhook", json=event)
    assert first.status_code == 200 and first.json()["duplicate"] is False

    second = client.post("/api/payments/webhook", json=event)
    assert second.status_code == 200
    ack = second.json()
    assert ack["received"] is True and ack["duplicate"] is True
    assert ack["booking_status"] == "CONFIRMED"          # state not corrupted

    third = client.post("/api/payments/webhook", json=event)
    assert third.status_code == 200 and third.json()["duplicate"] is True

    # Only one logical event/payment exists despite three deliveries.
    assert db_session.query(Payment).filter_by(provider_event_id="evt_test_dup_01").count() == 1
    assert db_session.query(Payment).count() == 1


def test_conflicting_event_for_confirmed_booking_rejected(client, user, booking):
    ok = client.post("/api/payments/webhook", json=_webhook("evt_test_conf_01", booking["id"], "SUCCESS"))
    assert ok.status_code == 200

    # A different event_id cannot demote a confirmed booking to FAILED.
    res = client.post("/api/payments/webhook", json=_webhook("evt_test_conf_02", booking["id"], "FAILED"))
    assert res.status_code == 409

    shown = client.get(f"/api/bookings/{booking['id']}", headers=user["headers"])
    assert shown.json()["status"] == "CONFIRMED"


def test_failed_event_id_reused_for_other_booking_rejected(client, user, booking):
    """Same event_id pointing at a different booking is a conflict, not a silent no-op."""
    client.post("/api/payments/webhook", json=_webhook("evt_test_reuse_01", booking["id"], "SUCCESS"))

    register(client, email="other@example.com", password="secret456", name="Other User")
    other_headers = auth_header(client, email="other@example.com", password="secret456")
    other_booking = client.post("/api/bookings", headers=other_headers, json={
        "centre_test_id": booking["centre_test_id"],
        "appointment_datetime": "2027-05-01T10:00:00+00:00",
    }).json()

    res = client.post("/api/payments/webhook", json=_webhook("evt_test_reuse_01", other_booking["id"], "SUCCESS"))
    assert res.status_code == 409


def test_failed_payment_then_webhook_success_path(client, user, booking, catalogue):
    """Failed simulated payment -> booking FAILED -> cancellation allowed."""
    client.post("/api/payments", headers=user["headers"],
                json={"booking_id": booking["id"], "simulate": "failure"})
    shown = client.get(f"/api/bookings/{booking['id']}", headers=user["headers"])
    assert shown.json()["status"] == "FAILED"

    res = client.patch(f"/api/bookings/{booking['id']}/cancel", headers=user["headers"])
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"
