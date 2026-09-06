"""
models.py
---------
This file defines our two database tables as Python classes, using
SQLAlchemy's ORM. Each class = one table. Each attribute = one column.

These match the schema in database.sql exactly.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # bcrypt hash, never plain text
    created_at = Column(DateTime, server_default=func.now())

    # One user can have many shortened URLs.
    # This is not a database column - it's a convenience for Python code,
    # e.g. some_user.urls gives you a list of that user's Url objects.
    urls = relationship("Url", back_populates="owner", cascade="all, delete-orphan")


class Url(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String(2048), nullable=False)
    short_code = Column(String(10), unique=True, nullable=False, index=True)
    click_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, server_default=func.now())
    last_accessed = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Lets us do some_url.owner to get the User object that created it.
    owner = relationship("User", back_populates="urls")
