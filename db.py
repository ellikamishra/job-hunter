"""
Postgres database (Supabase) for user accounts, saved searches,
uploaded company lists, and scraped job history.
"""
import hashlib
import json
import os
import secrets
from datetime import datetime

import psycopg2
import psycopg2.extras


def _get_db_url() -> str:
    url = os.environ.get("SUPABASE_DB_URL", "")
    if url:
        return url
    try:
        import streamlit as st
        return st.secrets["SUPABASE_DB_URL"]
    except Exception:
        return ""


def _get_conn():
    url = _get_db_url()
    if not url:
        raise RuntimeError(
            "SUPABASE_DB_URL not set. Add it as an environment variable "
            "or in .streamlit/secrets.toml"
        )
    conn = psycopg2.connect(url)
    conn.autocommit = False
    return conn


# ── Auth helpers ────────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def create_user(email: str, password: str) -> int | None:
    """Create a user. Returns user id or None if email exists."""
    salt = secrets.token_hex(16)
    hashed = _hash_password(password, salt)
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email, password, salt) VALUES (%s, %s, %s) RETURNING id",
            (email.lower().strip(), hashed, salt),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return user_id
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict | None:
    """Return user row dict if credentials match, else None."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    if _hash_password(password, row["salt"]) != row["password"]:
        return None
    return dict(row)


# ── Saved searches ──────────────────────────────────────────────────────────

def save_search(user_id: int, name: str, field: str, skills: list,
                locations: list, experience: list, categories: list,
                source_mode: str, scrape_location: str,
                company_limit: int, notify_email: bool) -> int:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO saved_searches
                (user_id, name, field, skills, locations, experience, categories,
                 source_mode, scrape_location, company_limit, notify_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, name, field,
            json.dumps(skills), json.dumps(locations), json.dumps(experience),
            json.dumps(categories), source_mode, scrape_location,
            company_limit, int(notify_email),
        ))
        search_id = cur.fetchone()[0]
        conn.commit()
        return search_id
    finally:
        conn.close()


def update_search(search_id: int, **kwargs):
    conn = _get_conn()
    try:
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in ("skills", "locations", "experience", "categories"):
                v = json.dumps(v)
            if k == "notify_email":
                v = int(v)
            sets.append(f"{k} = %s")
            vals.append(v)
        sets.append("updated_at = NOW()")
        vals.append(search_id)
        cur = conn.cursor()
        cur.execute(f"UPDATE saved_searches SET {', '.join(sets)} WHERE id = %s", vals)
        conn.commit()
    finally:
        conn.close()


def _parse_search_row(d: dict) -> dict:
    """Parse JSON fields and booleans in a search row."""
    for k in ("skills", "locations", "experience", "categories"):
        d[k] = json.loads(d[k])
    d["notify_email"] = bool(d["notify_email"])
    d["active"] = bool(d["active"])
    return d


def get_searches(user_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM saved_searches WHERE user_id = %s ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [_parse_search_row(dict(r)) for r in rows]


def get_search(search_id: int) -> dict | None:
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM saved_searches WHERE id = %s", (search_id,))
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    return _parse_search_row(dict(row))


def delete_search(search_id: int):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM uploaded_companies WHERE search_id = %s", (search_id,))
        cur.execute("DELETE FROM job_results WHERE search_id = %s", (search_id,))
        cur.execute("DELETE FROM saved_searches WHERE id = %s", (search_id,))
        conn.commit()
    finally:
        conn.close()


def get_active_searches() -> list[dict]:
    """Return all active searches across all users (for scheduler)."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT s.*, u.email
            FROM saved_searches s
            JOIN users u ON u.id = s.user_id
            WHERE s.active = 1
            ORDER BY s.updated_at DESC
        """)
        rows = cur.fetchall()
    finally:
        conn.close()
    return [_parse_search_row(dict(r)) for r in rows]


# ── Uploaded companies ──────────────────────────────────────────────────────

def save_uploaded_companies(user_id: int, search_id: int, companies: list[dict]):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM uploaded_companies WHERE search_id = %s", (search_id,))
        for c in companies:
            cur.execute("""
                INSERT INTO uploaded_companies (user_id, search_id, name, domain, career_url)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, search_id, c["name"], c["domain"], c.get("career_url", "")))
        conn.commit()
    finally:
        conn.close()


def get_uploaded_companies(search_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT name, domain, career_url FROM uploaded_companies WHERE search_id = %s",
            (search_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ── Job results ─────────────────────────────────────────────────────────────

def save_job_results(user_id: int, search_id: int, jobs: list[dict]) -> int:
    """Save jobs and return the count of NEW jobs (not previously seen)."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        new_count = 0
        for j in jobs:
            cur.execute("""
                INSERT INTO job_results
                    (user_id, search_id, company, title, location, experience,
                     skills, posted_date, link)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (search_id, link) DO NOTHING
            """, (
                user_id, search_id,
                j.get("company", ""), j.get("title", ""),
                j.get("location", ""), j.get("experience", ""),
                j.get("skills_matched", ""), j.get("posted_date", ""),
                j.get("link", ""),
            ))
            new_count += cur.rowcount
        conn.commit()
        return new_count
    finally:
        conn.close()


def get_job_results(search_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM job_results WHERE search_id = %s ORDER BY found_at DESC",
            (search_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_unnotified_jobs(search_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM job_results WHERE search_id = %s AND notified = 0 ORDER BY found_at DESC",
            (search_id,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def mark_jobs_notified(search_id: int):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE job_results SET notified = 1 WHERE search_id = %s AND notified = 0",
            (search_id,),
        )
        conn.commit()
    finally:
        conn.close()
