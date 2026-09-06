# 🔗 Linklytics (Python Edition)

## Project Overview

Linklytics is a simple URL shortener. Users register and log in with a
username and password, then paste in long URLs to get short, shareable
links. Every short link redirects back to the original URL and keeps
track of how many times it's been clicked, so users can view basic
analytics on their own links. This is a from-scratch Python rebuild of
an earlier Java/Spring Boot version, built to be small, readable, and
easy to explain in an interview rather than production-grade.

## Features

- User registration
- User login
- JWT authentication (stateless, token-based)
- URL shortening with unique Base62 short codes
- URL redirection (short link → original link)
- Basic click analytics (click count, created date, last accessed)
- "My Links" page listing everything a user has shortened

## Architecture

```
Streamlit (frontend)  --HTTP-->  FastAPI (backend)  -->  SQLAlchemy (ORM)  -->  MySQL (database)
```

- **Streamlit** is the UI. It's just a Python script that renders forms,
  tables, and buttons — no HTML/CSS/JS to write. It talks to the backend
  purely over plain HTTP using the `requests` library, exactly like a
  browser-based frontend would.
- **FastAPI** is the web framework serving the REST API. It validates
  incoming JSON with Pydantic, handles routing, and returns JSON responses.
- **SQLAlchemy** is the ORM (Object Relational Mapper). It lets the backend
  work with Python classes (`User`, `Url`) instead of writing raw SQL for
  every query, and translates that into actual SQL statements.
- **MySQL** is the actual database that stores users and URLs on disk.

Because Streamlit and FastAPI are two separate processes (usually on two
different ports), the backend needs CORS enabled so the browser allows
Streamlit's page to call the FastAPI server.

## Project Structure

```
linklytics-python/
│
├── backend/
│   ├── main.py            ← FastAPI app entry point, creates tables, CORS, mounts routes
│   ├── database.py        ← SQLAlchemy engine/session setup, get_db() dependency
│   ├── models.py          ← SQLAlchemy ORM models: User, Url (the actual DB tables)
│   ├── schemas.py         ← Pydantic request/response models (the API's JSON contract)
│   ├── auth.py            ← Password hashing (bcrypt) + JWT creation/verification
│   ├── routes.py          ← All API endpoints (register, login, shorten, stats, redirect...)
│   ├── url_service.py     ← Base62 short-code generation logic
│   ├── database.sql       ← Run this once to create the database + tables
│   ├── requirements.txt   ← All Python dependencies (backend, frontend, tests)
│   └── tests/
│       └── test_api.py    ← Basic pytest tests (see note in that file about SQLite)
│
├── frontend/
│   └── app.py              ← The entire Streamlit UI (Register/Login/Dashboard/My Links/Analytics)
│
├── .env.example             ← Template for your local secrets/config
├── README.md                ← This file
└── INTERVIEW_GUIDE.md        ← Talking points + Q&A for explaining this project
```

## Prerequisites

- Python 3.11+
- MySQL 8 (server running locally)

## Setup (Windows PowerShell)

### 1. Create and activate a virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r backend\requirements.txt
```

### 3. Create the MySQL database

Open MySQL Command Line Client (or Workbench) and run the provided script:

```powershell
mysql -u root -p < backend\database.sql
```

This creates the `linklytics_db` database along with the `users` and `urls`
tables.

### 4. Configure your `.env` file

Copy the example file and fill in your own MySQL password and a JWT secret:

```powershell
copy .env.example .env
```

Then open `.env` and edit:

```
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/linklytics_db
JWT_SECRET=some_long_random_string
```

You can generate a random secret with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run the backend

```powershell
cd backend
uvicorn main:app --reload
```

The API is now running at **http://localhost:8000**. Interactive docs are
available at **http://localhost:8000/docs**.

**Keep this terminal window open.**

### 6. Run the frontend (in a second terminal)

```powershell
venv\Scripts\activate
streamlit run frontend\app.py
```

Streamlit will open your browser automatically at **http://localhost:8501**.

## API Reference

| Method | Endpoint                     | Auth      | Body                       |
|--------|-------------------------------|-----------|-----------------------------|
| POST   | `/api/auth/register`          | Public    | `{username, email, password}` |
| POST   | `/api/auth/login`             | Public    | `{username, password}`      |
| POST   | `/api/url/shorten`            | JWT       | `{original_url}`            |
| GET    | `/api/url/stats/{short_code}` | JWT (owner)| —                           |
| GET    | `/api/url/my-links`           | JWT       | —                            |
| GET    | `/{short_code}`               | Public    | — (302 redirect)            |

## Example Flow

1. **Register** a new account on the Streamlit "Register" tab (or `POST /api/auth/register`).
2. **Log in** — the backend returns a JWT token, which Streamlit stores in
   `st.session_state` (or you keep it in a shell variable if testing with curl).
3. **Shorten a URL** from the Dashboard — the backend generates a random
   Base62 short code, stores it in MySQL, and returns the full short link.
4. **Open the short URL** in a browser — the backend looks it up, increments
   `click_count`, updates `last_accessed`, and issues a 302 redirect to the
   original URL.
5. **View Analytics** — paste the short code back in to see click count,
   created date, and last accessed time.
6. **My Links** — see a table of everything you've shortened so far.

## Running Tests

```powershell
cd backend
pytest
```

The tests use a temporary SQLite file instead of MySQL, purely to keep
automated testing simple and dependency-free (see the comment at the top
of `tests/test_api.py`). The real application always uses MySQL.