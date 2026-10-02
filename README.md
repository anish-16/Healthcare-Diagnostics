# Healthcare — Diagnostic Booking Backend Platform

A FastAPI + PostgreSQL backend for booking diagnostic tests. Authenticated users browse
diagnostic centres and tests, create bookings (prices are always resolved server-side),
pay through a **simulated** payment service, and a provider-style webhook applies payment
outcomes **idempotently**.

> **This is a backend-only submission** (no frontend, no real payment gateway). Everything
> is demonstrable through Swagger UI (`/docs`) and raw HTTP requests.

---

## 1. Features

- **JWT authentication** — signup / login / `me`, bcrypt password hashing, bearer-protected routes.
- **Catalogue** — diagnostic centres and tests with a many-to-many `centre_tests` table;
  the same test can be offered by several centres at different prices.
- **Bookings** — authenticated users book a specific centre+test combination for a future
  appointment. The amount is **always copied from the catalogue row on the server** — the
  client never sends money values.
- **Booking lifecycle** — explicit state machine (`PENDING → CONFIRMED / FAILED / CANCELLED`)
  with transition rules enforced in one place; clients cannot set statuses directly.
- **Simulated payments** — deterministic success/failure outcomes (no random behaviour),
  one transaction for the payment row + booking status change.
- **Idempotent provider webhook** — replays of the same event are detected by a database
  unique constraint, not by in-memory state; conflicting events are rejected.
- **Ownership enforcement** — bookings and payments are scoped to the authenticated user
  in every query; cross-user access is rejected.
- **Migrations + seed data** — Alembic schema from scratch, repeatable seed script.
- **48 tests** (pytest + httpx/TestClient) against an isolated PostgreSQL test database.

## 2. Tech stack

| Layer      | Choice                                             |
|------------|----------------------------------------------------|
| Framework  | FastAPI 0.115 (Python 3.12/3.13)                   |
| Database   | PostgreSQL 16 (works on any recent 14+)            |
| ORM        | SQLAlchemy 2.0 (sync, declarative `Mapped` style)  |
| Migrations | Alembic 1.16                                       |
| Validation | Pydantic v2 + pydantic-settings (env config)       |
| Auth       | PyJWT (HS256 bearer tokens), passlib+bcrypt        |
| Testing    | pytest + Starlette TestClient (httpx)              |
| Docs       | OpenAPI 3.1 via Swagger UI at `/docs`              |

## 3. Project structure

```
app/
  main.py               # FastAPI app, router registration
  seed.py               # repeatable demo data (python -m app.seed)
  core/
    config.py           # pydantic-settings (env vars)
    database.py         # engine (UTC-pinned), SessionLocal, Base, get_db
    security.py         # bcrypt hashing + JWT encode/decode
  models/
    enums.py            # statuses + allowed booking transitions
    models.py           # User, DiagnosticCentre, DiagnosticTest, CentreTest, Booking, Payment
  schemas/              # Pydantic request/response models
    auth.py  catalog.py  booking.py  payment.py
  routers/              # thin HTTP layer
    auth.py  centres.py  tests.py  bookings.py  payments.py
  services/
    auth_service.py     # signup/login logic
    booking_service.py  # booking + payment + webhook business logic
  dependencies/
    auth.py             # OAuth2 bearer → current user
alembic/
  env.py                # wired to app settings + metadata
  versions/0001_initial_schema.py
tests/                  # pytest suite (isolated eve_health_test database)
alembic.ini  Dockerfile  docker-compose.yml  requirements.txt  .env.example
```

## 4. Setup (local, no Docker)

### Prerequisites

- Python 3.12+ and a running PostgreSQL 14+ instance.

### Steps

```bash
# 1. Create the databases (psql or any client)
createdb eve_health          # or: CREATE DATABASE eve_health;
# tests automatically create eve_health_test if missing

# 2. Virtual environment + dependencies
python -m venv .venv
source .venv/bin/activate            # Windows Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt

# 3. Environment variables
cp .env.example .env                 # then edit DATABASE_URL / SECRET_KEY

# 4. Schema
alembic upgrade head

# 5. Demo data (repeatable — safe to run again)
python -m app.seed

# 6. Run
uvicorn app.main:app --reload
```

- Swagger UI: **http://127.0.0.1:8000/docs**
- ReDoc: http://127.0.0.1:8000/redoc
- Health: `GET /health`

## 5. Environment variables (`.env`)

| Variable                          | Purpose                                        |
|-----------------------------------|------------------------------------------------|
| `DATABASE_URL`                    | SQLAlchemy URL, e.g. `postgresql+psycopg://postgres:postgres@localhost:5432/eve_health` |
| `TEST_DATABASE_URL`               | Database used by the test suite (`eve_health_test`) |
| `SECRET_KEY`                      | JWT signing secret — **use a long random value** |
| `JWT_ALGORITHM`                   | Default `HS256`                                |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime (default 60)                    |
| `BCRYPT_ROUNDS`                   | bcrypt cost (default 12; tests use 4 for speed)|

All timestamps are **UTC**: columns are `timestamptz`, the engine pins the session
timezone to UTC, and the API returns ISO-8601 with a `Z` offset.

## 6. Docker alternative

```bash
docker compose up --build
```

Starts PostgreSQL + the API, runs `alembic upgrade head` and the seed automatically.
Swagger: http://127.0.0.1:8000/docs. The compose file uses placeholder dev secrets.

## 7. API overview

| Method | Path                        | Auth   | Description |
|--------|-----------------------------|--------|-------------|
| POST   | `/api/auth/signup`          | —      | Create account (201, 409 duplicate, 422 invalid) |
| POST   | `/api/auth/login`           | —      | JSON `{email, password}` → `{access_token, token_type: "bearer"}` |
| GET    | `/api/auth/me`              | Bearer | Current user profile |
| GET    | `/api/centres`              | —      | List diagnostic centres |
| GET    | `/api/centres/{id}`         | —      | Centre detail |
| GET    | `/api/centres/{id}/tests`   | —      | Tests at that centre with per-centre prices |
| GET    | `/api/tests`                | —      | List diagnostic tests |
| GET    | `/api/tests/{id}`           | —      | Test detail |
| GET    | `/api/tests/{id}/offerings` | —      | Centres offering the test + prices |
| POST   | `/api/bookings`             | Bearer | Create booking (amount from catalogue) |
| GET    | `/api/bookings?status=`     | Bearer | List own bookings (optional status filter) |
| GET    | `/api/bookings/{id}`        | Bearer | Get own booking |
| PATCH  | `/api/bookings/{id}/cancel` | Bearer | Cancel (PENDING or FAILED only) |
| POST   | `/api/payments`             | Bearer | Simulated payment for own booking |
| GET    | `/api/payments`             | Bearer | List own payments |
| GET    | `/api/payments/{id}`        | Bearer | Get own payment |
| POST   | `/api/payments/webhook`     | —      | Provider payment events (idempotent) |

Swagger UI's **Authorize** button accepts the access token for the protected endpoints.

## 8. Authentication flow

```bash
curl -X POST http://127.0.0.1:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Aarav Sharma", "email": "aarav@example.com", "password": "secret123"}'
# 201 {"id": 1, "name": "Aarav Sharma", "email": "aarav@example.com", "created_at": "..."}

curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "aarav@example.com", "password": "secret123"}'
# 200 {"access_token": "eyJhbGciOi...", "token_type": "bearer"}

curl http://127.0.0.1:8000/api/auth/me -H "Authorization: Bearer <token>"
# 200 {"id": 1, ...}      — 401 without/with invalid or expired token
```

Passwords are bcrypt-hashed; the database stores only `hashed_password`. Duplicate
signups return **409** (checked in the service *and* enforced by a unique index on
`users.email`).

## 9. Booking

```bash
curl -X POST http://127.0.0.1:8000/api/bookings \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"centre_test_id": 1, "appointment_datetime": "2027-03-01T10:00:00+05:30"}'
# 201 {"id": 1, "amount": "299.00", "status": "PENDING",
#      "appointment_datetime": "2027-03-01T04:30:00Z", ...}
```

Key behaviours:

- **Server-side pricing** — the request carries only `centre_test_id`; the amount is the
  current `centre_tests.price`. Extra client fields (e.g. `amount`) are ignored.
- **Appointment validation** — must include a UTC offset (naive timestamps → 422) and be
  in the future (→ 422). Stored/returned in UTC.
- **Unknown `centre_test_id`** → 404.
- **Ownership** — `GET/PATCH .../bookings/{id}` and all payment endpoints scope by the
  token's user id; another user's booking returns **403** (its existence is never
  confirmed to non-owners).

### Booking lifecycle

```
            create                payment SUCCESS
  PENDING ─────────► ... no ... ► CONFIRMED   (terminal here)
     │  ▲
     │  └── payment FAILED ──► FAILED ──► CANCELLED (user)
     └────────────────────────► CANCELLED (user)
```

| From      | Allowed to                        | Trigger |
|-----------|-----------------------------------|---------|
| PENDING   | CONFIRMED, FAILED, CANCELLED      | payment result / cancel |
| CONFIRMED | —                                 | paid bookings are final (a refund flow is out of scope) |
| FAILED    | CANCELLED                         | user discards a failed booking |
| CANCELLED | —                                 | terminal |

Transitions live in `app/models/enums.py` (`BOOKING_TRANSITIONS`) and are enforced by
the service layer — violations return **409**. Clients have no endpoint that accepts a
status field, so `status=CONFIRMED` cannot be forged.

## 10. Simulated payments

`POST /api/payments` with `{"booking_id": <id>}` on the user's own **PENDING** booking.

- Amount always comes from the stored booking row.
- Outcome is **deterministic and controlled by the caller** — this is the documented
  simulation mechanism (no real gateway, no randomness):
  - omit `simulate` (or `"success"`) → payment `SUCCESS`, booking → `CONFIRMED`
  - `"simulate": "failure"` → payment `FAILED`, booking → `FAILED`
- The payment row and booking status update in **one database transaction**.
- Duplicate prevention: paying a non-PENDING booking → **409**
  (`CONFIRMED` → "already paid", `FAILED` → "create a new booking", `CANCELLED` → 409).
- A booking row is `SELECT ... FOR UPDATE`-locked during payment so two concurrent
  attempts cannot both succeed.
- The created payment gets a generated `provider_event_id` (`evt_sim_...`) mimicking the
  gateway's event reference.

## 11. Payment webhook (idempotent)

Simulated provider events are delivered to `POST /api/payments/webhook` (no bearer auth —
in production the provider's signature would be verified; see §15):

```json
{
  "event_id": "evt_live_demo_001",
  "booking_id": 3,
  "status": "SUCCESS"
}
```

Responses:

| Case                                                  | Response |
|-------------------------------------------------------|----------|
| First delivery, valid transition                      | `200 {"received": true, "duplicate": false, "payment_status": "...", "booking_status": "..."}` |
| **Replay of the same `event_id`**                     | `200 {"received": true, "duplicate": true, ...}` — **no state change** |
| Same `event_id` for a different booking               | `409` |
| `SUCCESS` after the booking is already `CONFIRMED` / `CANCELLED` (new event id) | `409` (invalid transition) |
| `FAILED` event for an already-`CONFIRMED` booking     | `409` — a finalized success is never demoted |
| Unknown `booking_id`                                  | `404` |
| Malformed payload / unknown status                    | `422` |

**Idempotency design.** The guarantee is the **unique index on
`payments.provider_event_id`**, not application memory:

1. The webhook locks the booking row (`SELECT ... FOR UPDATE`), so near-simultaneous
   deliveries for the same booking serialize.
2. It looks up `provider_event_id`; if present, it returns `duplicate: true` without
   writing anything.
3. Otherwise it inserts the payment row and updates the booking **in one transaction**.
   If a concurrent identical delivery committed first, the insert raises an
   `IntegrityError` on the unique index → the transaction is rolled back and the event is
   acknowledged as a duplicate. A replay therefore can never create a second payment or
   corrupt booking state, no matter how the events race.

The same replay test is exercised in `tests/test_payments.py::test_duplicate_webhook_delivery_is_idempotent`
(the same event is delivered three times; exactly one payment row exists and the booking
stays `CONFIRMED`).

## 12. Data model

```mermaid
erDiagram
    users ||--o{ bookings : "books"
    diagnostic_centres ||--o{ centre_tests : "offers"
    diagnostic_tests  ||--o{ centre_tests : "offered as"
    centre_tests      ||--o{ bookings  : "booked as"
    bookings          ||--o{ payments  : "paid via"

    users {
        int id PK
        varchar name
        varchar email UK
        varchar hashed_password
        timestamptz created_at
        timestamptz updated_at
    }
    diagnostic_centres {
        int id PK
        varchar name
        varchar location
    }
    diagnostic_tests {
        int id PK
        varchar name
        varchar description
    }
    centre_tests {
        int id PK
        int centre_id FK
        int test_id FK
        numeric price
    }
    bookings {
        int id PK
        int user_id FK
        int centre_test_id FK
        timestamptz appointment_datetime
        numeric amount
        varchar status
    }
    payments {
        int id PK
        int booking_id FK
        varchar provider_event_id UK
        numeric amount
        varchar status
    }
```

Design notes:

- `centre_tests` is an explicit association table (`UNIQUE (centre_id, test_id)`) because
  the **price belongs to the pair** — the same test costs differently per centre.
- `bookings.amount` is a snapshot of the price at booking time; later catalogue price
  changes don't rewrite history.
- `payments.provider_event_id` is `UNIQUE` — this is the webhook idempotency anchor.
- Money is `NUMERIC(10,2)` / Python `Decimal` everywhere; JSON responses carry decimal
  strings (`"299.00"`) to avoid float artefacts.
- Indexes: `users.email` (unique), `bookings(user_id, centre_test_id, status,
  appointment_datetime)`, `payments(booking_id)`, `payments(provider_event_id)` (unique).

## 13. API flow

```mermaid
flowchart TD
    A[POST /api/auth/signup] --> B[POST /api/auth/login]
    B --> C[JWT access_token]
    C --> D[GET /api/centres, /api/tests, /api/centres/id/tests]
    D --> E[POST /api/bookings  amount from centre_tests.price]
    E --> F[Booking PENDING]
    F --> G{POST /api/payments<br/>simulate?}
    G -- success --> H[Payment SUCCESS / Booking CONFIRMED]
    G -- failure --> I[Payment FAILED / Booking FAILED]
    F -. provider event .-> J[POST /api/payments/webhook]
    J -- SUCCESS --> H2[Payment SUCCESS / Booking CONFIRMED]
    J -- FAILED --> I2[Payment FAILED / Booking FAILED]
    J -. same event_id replay .-> K[200 duplicate: true, no change]
```

## 14. Validation & error handling

- **Pydantic v2 schemas** validate every request body (emails, password length +
  letter/digit rule, positive ids, enum statuses, datetime with offset, webhook fields).
  Invalid input → **422** with a field-level error list.
- **Business rules** raise clean HTTP errors from the service layer:
  `400` (invalid state input), `401` (missing/invalid/expired token or bad credentials),
  `403` (resource owned by another user), `404` (unknown resource), `409` (duplicate
  email, duplicate payment, invalid state transitions, event-id conflicts).
- Error bodies are `{"detail": "..."}` only — no stack traces or DB internals.

## 15. Assumptions

1. **Payments are fully simulated.** No Razorpay/Stripe/PayPal integration; outcomes are
   controlled via the `simulate` field so both paths are reproducible and testable.
2. The webhook is unauthenticated because a real provider authenticates via request
   signing; that is deliberately listed as an improvement, not faked here.
3. Cross-user resource access returns **403** (explicit denial) rather than 404.
4. Cancelling a **CONFIRMED** (paid) booking is not allowed — it would require a refund
   flow. `PENDING` and `FAILED` bookings can be cancelled.
5. A failed payment is terminal for that booking (create a new booking to retry); a
   payment-retry flow is out of scope.
6. No admin CRUD for centres/tests — catalogue data comes from the seed script; any
   management API would need a role/permission layer first.
7. Single server instance; no distributed locking beyond PostgreSQL row locks.

## 16. Tests

```bash
# uses TEST_DATABASE_URL (default postgresql+psycopg://postgres:postgres@localhost:5432/eve_health_test);
# the test database is created automatically and truncated between tests
pytest -q
```

48 tests cover: signup success/duplicate/invalid, login success/invalid, protected
endpoint without/garbled token, centre & test retrieval with per-centre prices, booking
creation with server-side price (including a client-sent `amount` being ignored),
invalid centre/test combination, past/naive appointment rejection, unauthorized access to
another user's booking/payment, successful & failed simulated payments, duplicate payment
prevention, payment on cancelled bookings, webhook success/failure, malformed webhook
payloads, unknown booking webhook, **duplicate webhook delivery (same event sent three
times → one payment row, stable state)**, conflicting status transitions, and
event-id reuse across bookings.

## 17. What I would improve with more time

- **Webhook signature verification** (HMAC + timestamp tolerance) instead of trusting
  payloads.
- **Webhook retry/backoff semantics** and a delivery log for observability.
- **Redis-based rate limiting** on auth endpoints and caching for the catalogue.
- **Background jobs** (e.g. Celery) for reminder emails / auto-cancellation of stale
  pending bookings.
- **Role-based access control + admin tooling** for catalogue management.
- **Structured logging and request IDs**, plus metrics/tracing.
- **Pagination and filtering** on list endpoints.
- More extensive **integration tests** (concurrent webhook races, migration-in-sync
  checks) and CI wiring.
- **Deployment hardening**: per-origin CORS, secrets management, TLS termination,
  connection pooling tuning.
