"""
routes.py
---------
All API endpoints live here. This is intentionally kept in a single file
(instead of splitting into controller/service/repository layers like the
original Java project) because the project is small enough that one file
stays easy to read and navigate.

Endpoints:
  POST /api/auth/register
  POST /api/auth/login
  POST /api/url/shorten          (JWT required)
  GET  /api/url/stats/{code}     (JWT required, owner only)
  GET  /api/url/my-links         (JWT required)
  GET  /{short_code}             (public, redirects)
"""

import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_user, hash_password, verify_password
from database import get_db
from models import Url, User
from schemas import (
    LoginRequest,
    RegisterRequest,
    ShortenRequest,
    TokenResponse,
    UrlResponse,
    UrlStatsResponse,
)
from url_service import generate_unique_short_code

load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

router = APIRouter()


def build_short_url(short_code: str) -> str:
    """Combines the configured BASE_URL with a short code, e.g.
    http://localhost:8000 + abc1234 -> http://localhost:8000/abc1234"""
    return f"{BASE_URL.rstrip('/')}/{short_code}"


def is_valid_url(value: str) -> bool:
    """Basic sanity check: the URL must have a scheme (http/https) and a
    network location (domain). We deliberately keep this simple rather
    than writing a full RFC-3986 validator."""
    try:
        parsed = urlparse(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


# ============================================================
# AUTH ENDPOINTS
# ============================================================

@router.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Creates a new user account.

    Steps:
    1. Check username/email aren't already taken.
    2. Hash the password with bcrypt (never store plain text).
    3. Save the new user row.
    4. Log them in immediately by returning a JWT, so the frontend doesn't
       need a separate "please log in now" step.
    """
    existing = (
        db.query(User)
        .filter((User.username == payload.username) | (User.email == payload.email))
        .first()
    )
    if existing:
        field = "username" if existing.username == payload.username else "email"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"That {field} is already registered.",
        )

    new_user = User(
        username=payload.username,
        email=payload.email,
        password=hash_password(payload.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(new_user.id, new_user.username)
    return TokenResponse(access_token=token, user=new_user)


@router.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Checks credentials and returns a JWT on success.

    We intentionally return the SAME error message whether the username
    doesn't exist or the password is wrong - this avoids revealing which
    usernames are registered.
    """
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(user.id, user.username)
    return TokenResponse(access_token=token, user=user)


# ============================================================
# URL ENDPOINTS
# ============================================================

@router.post("/api/url/shorten", response_model=UrlResponse, status_code=status.HTTP_201_CREATED)
def shorten_url(
    payload: ShortenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a short code for the given URL, owned by the logged-in user."""
    if not is_valid_url(payload.original_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid URL starting with http:// or https://",
        )

    short_code = generate_unique_short_code(db, Url)

    new_url = Url(
        original_url=payload.original_url,
        short_code=short_code,
        user_id=current_user.id,
    )
    db.add(new_url)
    db.commit()
    db.refresh(new_url)

    return UrlResponse(
        id=new_url.id,
        original_url=new_url.original_url,
        short_code=new_url.short_code,
        short_url=build_short_url(new_url.short_code),
        click_count=new_url.click_count,
        created_at=new_url.created_at,
        last_accessed=new_url.last_accessed,
    )


@router.get("/api/url/stats/{short_code}", response_model=UrlStatsResponse)
def get_url_stats(
    short_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns click stats for a short code. Only the owner may view them."""
    url = db.query(Url).filter(Url.short_code == short_code).first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found.")

    if url.user_id != current_user.id:
        # 403, not 404: the code exists, the caller just isn't allowed to see it.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this URL's statistics.",
        )

    return url


@router.get("/api/url/my-links", response_model=list[UrlResponse])
def get_my_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns every short URL created by the logged-in user, newest first."""
    urls = (
        db.query(Url)
        .filter(Url.user_id == current_user.id)
        .order_by(Url.created_at.desc())
        .all()
    )

    return [
        UrlResponse(
            id=u.id,
            original_url=u.original_url,
            short_code=u.short_code,
            short_url=build_short_url(u.short_code),
            click_count=u.click_count,
            created_at=u.created_at,
            last_accessed=u.last_accessed,
        )
        for u in urls
    ]


@router.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    """
    Public endpoint. Looks up the short code, bumps the click counter and
    last_accessed timestamp, then redirects the browser to the original URL.

    We use a 302 (temporary) redirect rather than 301 (permanent) because
    browsers cache 301s aggressively - a cached redirect would skip our
    server entirely on the next visit, and we'd stop counting clicks.
    """
    url = db.query(Url).filter(Url.short_code == short_code).first()

    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found.")

    # A single UPDATE-like operation via the ORM; SQLAlchemy issues one
    # UPDATE statement when we commit, so there's no read-then-write race
    # condition window for this simple use case.
    url.click_count += 1
    url.last_accessed = datetime.now(timezone.utc)
    db.commit()

    return RedirectResponse(url=url.original_url, status_code=status.HTTP_302_FOUND)
