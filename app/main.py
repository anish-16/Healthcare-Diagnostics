from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, bookings, centres, payments, tests

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Backend for booking diagnostic tests. Users sign up, browse centres and tests, "
        "create bookings (prices are always resolved server-side), pay through a simulated "
        "payment service, and the provider webhook applies payment outcomes idempotently. "
        "All timestamps are UTC."
    ),
    swagger_ui_parameters={"persistAuthorization": True},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # backend-only assignment; tighten per-origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(tests.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", tags=["Health"], summary="Liveness probe")
def health():
    return {"status": "ok"}
