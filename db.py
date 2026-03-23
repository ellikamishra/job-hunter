"""
SQLite database for user accounts, saved searches, uploaded company lists,
and scraped job history.
"""
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "job_hunter.db")


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            salt        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS saved_searches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES users(id),
            name            TEXT    NOT NULL DEFAULT 'My Search',
            field           TEXT    NOT NULL DEFAULT '',
            skills          TEXT    NOT NULL DEFAULT '[]',
            locations       TEXT    NOT NULL DEFAULT '[]',
            experience      TEXT    NOT NULL DEFAULT '[]',
            categories      TEXT    NOT NULL DEFAULT '[]',
            source_mode     TEXT    NOT NULL DEFAULT 'Auto-generate from location',
            scrape_location TEXT    NOT NULL DEFAULT 'any',
            company_limit   INTEGER NOT NULL DEFAULT 50,
            notify_email    INTEGER NOT NULL DEFAULT 1,
            active          INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS uploaded_companies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            search_id   INTEGER REFERENCES saved_searches(id),
            name        TEXT    NOT NULL,
            domain      TEXT    NOT NULL,
            career_url  TEXT    NOT NULL DEFAULT '',
            uploaded_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS job_results (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            search_id   INTEGER NOT NULL REFERENCES saved_searches(id),
            company     TEXT    NOT NULL,
            title       TEXT    NOT NULL,
            location    TEXT    NOT NULL DEFAULT '',
            experience  TEXT    NOT NULL DEFAULT '',
            skills      TEXT    NOT NULL DEFAULT '',
            posted_date TEXT    NOT NULL DEFAULT '',
            link        TEXT    NOT NULL,
            found_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            notified    INTEGER NOT NULL DEFAULT 0
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_job_link_search
            ON job_results(search_id, link);
    """)
    conn.commit()
    conn.close()


# ── Auth helpers ────────────────────────────────────────────────────────────

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode()).hexdigest()


def create_user(email: str, password: str) -> int | None:
    """Create a user. Returns user id or None if email exists."""
    salt = secrets.token_hex(16)
    hashed = _hash_password(password, salt)
    conn = _get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password, salt) VALUES (?, ?, ?)",
            (email.lower().strip(), hashed, salt),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict | None:
    """Return user row dict if credentials match, else None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
    ).fetchone()
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
    cur = conn.execute("""
        INSERT INTO saved_searches
            (user_id, name, field, skills, locations, experience, categories,
             source_mode, scrape_location, company_limit, notify_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, name, field,
        json.dumps(skills), json.dumps(locations), json.dumps(experience),
        json.dumps(categories), source_mode, scrape_location,
        company_limit, int(notify_email),
    ))
    conn.commit()
    search_id = cur.lastrowid
    conn.close()
    return search_id


def update_search(search_id: int, **kwargs):
    conn = _get_conn()
    sets = []
    vals = []
    for k, v in kwargs.items():
        if k in ("skills", "locations", "experience", "categories"):
            v = json.dumps(v)
        if k == "notify_email":
            v = int(v)
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = datetime('now')")
    vals.append(search_id)
    conn.execute(f"UPDATE saved_searches SET {', '.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def get_searches(user_id: int) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM saved_searches WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        for k in ("skills", "locations", "experience", "categories"):
            d[k] = json.loads(d[k])
        d["notify_email"] = bool(d["notify_email"])
        d["active"] = bool(d["active"])
        result.append(d)
    return result


def get_search(search_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM saved_searches WHERE id = ?", (search_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for k in ("skills", "locations", "experience", "categories"):
        d[k] = json.loads(d[k])
    d["notify_email"] = bool(d["notify_email"])
    d["active"] = bool(d["active"])
    return d


def delete_search(search_id: int):
    conn = _get_conn()
    conn.execute("DELETE FROM uploaded_companies WHERE search_id = ?", (search_id,))
    conn.execute("DELETE FROM job_results WHERE search_id = ?", (search_id,))
    conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
    conn.commit()
    conn.close()


def get_active_searches() -> list[dict]:
    """Return all active searches across all users (for scheduler)."""
    conn = _get_conn()
    rows = conn.execute("""
        SELECT s.*, u.email
        FROM saved_searches s
        JOIN users u ON u.id = s.user_id
        WHERE s.active = 1
        ORDER BY s.updated_at DESC
    """).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        for k in ("skills", "locations", "experience", "categories"):
            d[k] = json.loads(d[k])
        d["notify_email"] = bool(d["notify_email"])
        d["active"] = bool(d["active"])
        result.append(d)
    return result


# ── Uploaded companies ──────────────────────────────────────────────────────

def save_uploaded_companies(user_id: int, search_id: int, companies: list[dict]):
    conn = _get_conn()
    conn.execute("DELETE FROM uploaded_companies WHERE search_id = ?", (search_id,))
    for c in companies:
        conn.execute("""
            INSERT INTO uploaded_companies (user_id, search_id, name, domain, career_url)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, search_id, c["name"], c["domain"], c.get("career_url", "")))
    conn.commit()
    conn.close()


def get_uploaded_companies(search_id: int) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT name, domain, career_url FROM uploaded_companies WHERE search_id = ?",
        (search_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Job results ─────────────────────────────────────────────────────────────

def save_job_results(user_id: int, search_id: int, jobs: list[dict]) -> int:
    """Save jobs and return the count of NEW jobs (not previously seen)."""
    conn = _get_conn()
    new_count = 0
    for j in jobs:
        try:
            conn.execute("""
                INSERT INTO job_results
                    (user_id, search_id, company, title, location, experience,
                     skills, posted_date, link)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, search_id,
                j.get("company", ""), j.get("title", ""),
                j.get("location", ""), j.get("experience", ""),
                j.get("skills_matched", ""), j.get("posted_date", ""),
                j.get("link", ""),
            ))
            new_count += 1
        except sqlite3.IntegrityError:
            pass  # duplicate link for this search
    conn.commit()
    conn.close()
    return new_count


def get_job_results(search_id: int) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM job_results WHERE search_id = ? ORDER BY found_at DESC",
        (search_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unnotified_jobs(search_id: int) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM job_results WHERE search_id = ? AND notified = 0 ORDER BY found_at DESC",
        (search_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_jobs_notified(search_id: int):
    conn = _get_conn()
    conn.execute(
        "UPDATE job_results SET notified = 1 WHERE search_id = ? AND notified = 0",
        (search_id,),
    )
    conn.commit()
    conn.close()


# Initialize on import
init_db()
