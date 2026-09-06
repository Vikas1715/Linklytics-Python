"""
schemas.py
----------
Pydantic models describe the SHAPE of data going into and out of our API.

Why do we need these if we already have SQLAlchemy models (models.py)?
- models.py describes the DATABASE table.
- schemas.py describes the API's JSON contract (request bodies + responses).

Keeping them separate means:
- We never accidentally expose a field like `password` in an API response.
- FastAPI can auto-validate incoming JSON (e.g. reject a request with no email)
  and auto-generate the interactive docs at /docs.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Auth ----------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    # Allows Pydantic to read data straight from a SQLAlchemy object
    # (e.g. response_model=UserResponse combined with a User ORM instance).
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------- URLs ----------

class ShortenRequest(BaseModel):
    original_url: str = Field(min_length=1, max_length=2048)


class UrlResponse(BaseModel):
    id: int
    original_url: str
    short_code: str
    short_url: str  # full clickable link, e.g. http://localhost:8000/abc123
    click_count: int
    created_at: datetime
    last_accessed: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UrlStatsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    last_accessed: datetime | None

    model_config = ConfigDict(from_attributes=True)
