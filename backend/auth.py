"""
auth.py
-------
Everything related to passwords and JWT tokens lives here. This is the
file to read if you want to understand:

  - How a password is hashed before it's stored.
  - How a password is checked at login.
  - How a JWT token is created after a successful login.
  - How a JWT token is verified on protected endpoints.
  - How we figure out "who is the current logged-in user" from a token.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import User

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# This tells FastAPI to expect an "Authorization: Bearer <token>" header
# on any route that depends on it.
bearer_scheme = HTTPBearer()


# ---------- Password hashing ----------

def hash_password(plain_password: str) -> str:
    """
    Turns a plain-text password into a bcrypt hash before we store it.
    bcrypt automatically generates and embeds a random "salt" in the hash,
    so two users with the same password get different hashes.
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Checks a plain-text password against the stored hash at login time.
    We NEVER decrypt the hash - bcrypt re-hashes the plain password with
    the same salt and compares the two hashes.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ---------- JWT tokens ----------

def create_access_token(user_id: int, username: str) -> str:
    """
    Builds a JWT for a user right after they log in.

    A JWT has 3 parts: header.payload.signature
    - The "payload" below is the data we store INSIDE the token
      (it is base64-encoded, NOT encrypted - anyone can read it,
      but only we can produce a valid signature for it).
    - "exp" is a standard claim that says when the token expires.
      PyJWT automatically rejects expired tokens when decoding.
    """
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),   # "subject" = who this token belongs to
        "username": username,
        "exp": expire_at,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> dict:
    """
    Verifies the token's signature and expiry, and returns its payload.
    Raises jwt exceptions if the token is invalid/expired - callers should
    catch these (see get_current_user below).
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency used on every protected route, e.g.:

        def my_route(current_user: User = Depends(get_current_user)):
            ...

    Steps:
    1. FastAPI extracts the token from the "Authorization: Bearer <token>" header.
    2. We decode + verify it.
    3. We look up the matching User row in the database.
    4. If anything fails, we raise a 401 Unauthorized error.
    """
    token = credentials.credentials
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_error

    return user
