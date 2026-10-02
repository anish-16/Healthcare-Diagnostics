from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.dependencies.auth import get_current_user
from app.models.models import User
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             summary="Create a new user account")
def signup(payload: SignupRequest, db: Annotated[Session, Depends(get_db)]):
    return auth_service.signup(db, payload)


@router.post("/login", response_model=TokenResponse, summary="Log in and get a JWT access token")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = auth_service.login(db, payload)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut, summary="Get the authenticated user's profile")
def me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
