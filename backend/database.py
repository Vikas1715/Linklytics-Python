"""
database.py
------------
This file sets up the connection to MySQL using SQLAlchemy.

SQLAlchemy is an ORM (Object Relational Mapper). It lets us work with
database rows as if they were normal Python objects, instead of writing
raw SQL everywhere.

Three things happen here:
1. We build an "engine" - the actual connection to MySQL.
2. We build a "SessionLocal" factory - each request gets its own session
   (a session is like a temporary workspace for talking to the database).
3. We build a "Base" class - every table model (User, Url) inherits from
   this so SQLAlchemy knows about them.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load variables from the .env file into the environment
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/linklytics_db",
)

# The engine manages the actual pool of connections to MySQL.
# pool_pre_ping=True checks that a connection is still alive before using it,
# which avoids "MySQL server has gone away" errors after idle time.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal is a factory that creates new Session objects.
# We create one Session per API request (see get_db() in routes.py).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our ORM models (User, Url) will inherit from this Base class.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session to a route,
    and makes sure it is always closed afterwards (even if an error occurs).

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
