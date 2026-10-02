from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120, examples=["Aarav Sharma"])
    email: EmailStr = Field(examples=["aarav@example.com"])
    # At least 8 chars with one letter and one digit — readable rule, enforced in one place.
    password: str = Field(min_length=8, max_length=128, examples=["secret123"])

    @field_validator("password")
    @classmethod
    def needs_letter_and_digit(cls, value: str) -> str:
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one letter and one digit")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["aarav@example.com"])
    password: str = Field(min_length=1, examples=["secret123"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
