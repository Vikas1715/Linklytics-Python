"""
app.py (Streamlit frontend)
----------------------------
A very simple UI for the Linklytics API. No fancy styling - just enough
to register, log in, shorten URLs, and view stats.

How it talks to the backend:
    Every button click sends a plain HTTP request (via the `requests`
    library) to the FastAPI server, then displays the JSON response.

Session state:
    Streamlit re-runs this whole script top-to-bottom every time you
    interact with a widget. `st.session_state` is the one thing that
    survives between re-runs, so we store the JWT token and username
    there once the user logs in.

Run with (from the project root):
    streamlit run frontend/app.py
"""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Linklytics", page_icon="🔗")

# ---------- session state defaults ----------
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None


def auth_headers():
    """Builds the Authorization header using the token stored in session state."""
    return {"Authorization": f"Bearer {st.session_state.token}"}


def logout():
    st.session_state.token = None
    st.session_state.username = None


# ============================================================
# LOGGED OUT VIEW: show Register / Login tabs
# ============================================================
if not st.session_state.token:
    st.title("🔗 Linklytics")
    st.caption("A simple URL shortener")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            response = requests.post(
                f"{API_URL}/api/auth/login",
                json={"username": login_username, "password": login_password},
            )
            if response.status_code == 200:
                data = response.json()
                st.session_state.token = data["access_token"]
                st.session_state.username = data["user"]["username"]
                st.success("Logged in! Redirecting to dashboard...")
                st.rerun()
            else:
                st.error(response.json().get("detail", "Login failed."))

    with tab_register:
        st.subheader("Create an account")
        reg_username = st.text_input("Username", key="reg_username")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_password")

        if st.button("Register"):
            response = requests.post(
                f"{API_URL}/api/auth/register",
                json={
                    "username": reg_username,
                    "email": reg_email,
                    "password": reg_password,
                },
            )
            if response.status_code == 201:
                st.success("Account created! Please log in from the Login tab.")
            else:
                st.error(response.json().get("detail", "Registration failed."))

# ============================================================
# LOGGED IN VIEW: Dashboard / My Links / Analytics
# ============================================================
else:
    st.sidebar.write(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    page = st.sidebar.radio("Go to", ["Dashboard", "My Links", "Analytics"])

    # ---------------- Dashboard ----------------
    if page == "Dashboard":
        st.title("Dashboard")
        st.subheader("Shorten a URL")

        original_url = st.text_input("Paste a long URL here", placeholder="https://example.com/some/long/path")

        if st.button("⚡ Shorten"):
            response = requests.post(
                f"{API_URL}/api/url/shorten",
                json={"original_url": original_url},
                headers=auth_headers(),
            )
            if response.status_code == 201:
                data = response.json()
                st.success("Here's your short link:")
                st.code(data["short_url"])
            else:
                st.error(response.json().get("detail", "Could not shorten that URL."))

    # ---------------- My Links ----------------
    elif page == "My Links":
        st.title("My Links")

        response = requests.get(f"{API_URL}/api/url/my-links", headers=auth_headers())
        if response.status_code == 200:
            links = response.json()
            if not links:
                st.info("You haven't shortened any URLs yet.")
            else:
                table_rows = [
                    {
                        "Short URL": link["short_url"],
                        "Original URL": link["original_url"],
                        "Clicks": link["click_count"],
                        "Created At": link["created_at"],
                        "Last Accessed": link["last_accessed"] or "Never",
                    }
                    for link in links
                ]
                st.table(table_rows)
        else:
            st.error("Could not load your links.")

    # ---------------- Analytics ----------------
    elif page == "Analytics":
        st.title("Analytics")
        st.subheader("Look up stats for a short code")

        short_code = st.text_input("Short code", placeholder="e.g. x4fkSPH")

        if st.button("Get Stats"):
            response = requests.get(
                f"{API_URL}/api/url/stats/{short_code}",
                headers=auth_headers(),
            )
            if response.status_code == 200:
                data = response.json()
                st.metric("Click Count", data["click_count"])
                st.write(f"**Original URL:** {data['original_url']}")
                st.write(f"**Created At:** {data['created_at']}")
                st.write(f"**Last Accessed:** {data['last_accessed'] or 'Never'}")
            else:
                st.error(response.json().get("detail", "Could not find that short code."))
