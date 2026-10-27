"""SQLite database layer for Blue Visual Teacher user accounts, sessions, and lesson ownership.

Follows project principles:
- Zero external dependencies: uses Python standard library `sqlite3` and `hashlib.pbkdf2_hmac`.
- Video files are NEVER stored as BLOBs; only relative paths, URLs, and metadata are saved in SQLite.
- Fast indexed queries, parameterized statements, foreign key integrity.
"""

import os
import sqlite3
import hashlib
import secrets
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "bvt.db"


def get_db_path() -> Path:
    db_file = os.environ.get("BVT_DB_PATH")
    if db_file:
        return Path(db_file)
    return DB_PATH


def init_db(db_path: Optional[Path] = None) -> None:
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                lang TEXT NOT NULL,
                status TEXT NOT NULL,
                pct INTEGER DEFAULT 0,
                stage TEXT DEFAULT 'queued',
                mp4_url TEXT,
                manifest_url TEXT,
                audio_url TEXT,
                error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lessons_user ON lessons(user_id, created_at DESC);")
        conn.commit()


# Password Hashing with PBKDF2-HMAC-SHA256 (100,000 iterations, 32-byte salt)
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(32)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{pwd_hash.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(expected, computed)
    except Exception:
        return False


def create_user(name: str, email: str, password: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    email_norm = email.strip().lower()
    name_clean = name.strip()
    if not email_norm or "@" not in email_norm:
        raise ValueError("Invalid email address")
    if len(name_clean) < 2:
        raise ValueError("Name must be at least 2 characters")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    user_id = secrets.token_hex(12)
    pwd_hash = hash_password(password)
    now = time.time()

    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            conn.execute(
                "INSERT INTO users (id, name, email, password_hash, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name_clean, email_norm, pwd_hash, now, now)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email already exists")

    return {"id": user_id, "name": name_clean, "email": email_norm, "created_at": now}


def authenticate_user(email: str, password: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    email_norm = email.strip().lower()
    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?", (email_norm,))
        row = cur.fetchone()
        if not row:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "name": row["name"], "email": row["email"], "created_at": row["created_at"]}


def create_session(user_id: str, max_age_seconds: int = 7 * 86400, db_path: Optional[Path] = None) -> str:
    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + max_age_seconds

    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now, expires_at)
        )
        conn.commit()
    return token


def get_user_from_session(token: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    now = time.time()
    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT u.id, u.name, u.email, u.created_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, now))
        row = cur.fetchone()
        if row:
            return dict(row)
    return None


def delete_session(token: str, db_path: Optional[Path] = None) -> None:
    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


# Lesson Persistence & Ownership
def record_lesson(
    lesson_id: str,
    user_id: str,
    topic: str,
    lang: str,
    status: str = "queued",
    pct: int = 0,
    stage: str = "queued",
    mp4_url: Optional[str] = None,
    manifest_url: Optional[str] = None,
    audio_url: Optional[str] = None,
    error: Optional[str] = None,
    db_path: Optional[Path] = None
) -> None:
    now = time.time()
    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("""
            INSERT INTO lessons (id, user_id, topic, lang, status, pct, stage, mp4_url, manifest_url, audio_url, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                pct = excluded.pct,
                stage = excluded.stage,
                mp4_url = COALESCE(excluded.mp4_url, lessons.mp4_url),
                manifest_url = COALESCE(excluded.manifest_url, lessons.manifest_url),
                audio_url = COALESCE(excluded.audio_url, lessons.audio_url),
                error = excluded.error,
                updated_at = excluded.updated_at;
        """, (lesson_id, user_id, topic, lang, status, pct, stage, mp4_url, manifest_url, audio_url, error, now, now))
        conn.commit()


def get_user_lessons(user_id: str, limit: int = 50, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("""
            SELECT id, user_id, topic, lang, status, pct, stage, mp4_url, manifest_url, audio_url, error, created_at, updated_at
            FROM lessons
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        return [dict(r) for r in cur.fetchall()]


def get_lesson_by_id(lesson_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    path = db_path or get_db_path()
    with sqlite3.connect(str(path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
    return None
