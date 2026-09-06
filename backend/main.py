"""
main.py
-------
The entry point of the backend. This is the file uvicorn runs.

Responsibilities:
1. Create the FastAPI app.
2. Create the database tables if they don't exist yet
   (Base.metadata.create_all - convenient for a small project;
   a production system would use migrations like Alembic instead).
3. Add CORS middleware so the Streamlit frontend (running on a different
   port) is allowed to call this API from the browser.
4. Include all routes from routes.py.

Run with:
    uvicorn main:app --reload
(from inside the backend/ folder)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
import models  # noqa: F401 - needed so SQLAlchemy knows about User/Url before create_all
from routes import router

# Creates the `users` and `urls` tables if they don't already exist.
# Safe to run every time the app starts - it does nothing if tables exist.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Linklytics API",
    description="A simple URL shortener with JWT authentication.",
    version="1.0.0",
)

# Streamlit runs on a different origin (e.g. localhost:8501) than the API
# (localhost:8000), so the browser needs explicit permission (CORS) to let
# JavaScript in one origin call the other. We allow all origins here since
# this only ever runs locally for this project.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    """Simple health-check endpoint."""
    return {"message": "Linklytics API is running. See /docs for the API reference."}
