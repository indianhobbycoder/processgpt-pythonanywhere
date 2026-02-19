"""Authentication and user persistence for ProcessGPT."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
USERS_DIR = BASE_DIR / "users"
DB_PATH = USERS_DIR / "users.db"


@dataclass(frozen=True)
class User:
    username: str
    role: str


def _connect() -> sqlite3.Connection:
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_user_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role in ('agent', 'trainer'))
            )
            """
        )
        conn.commit()

    # Seed default users only if they don't exist.
    if get_user("trainer1") is None:
        create_user("trainer1", "Trainer@123", "trainer")
    if get_user("agent1") is None:
        create_user("agent1", "Agent@123", "agent")


def create_user(username: str, password: str, role: str) -> None:
    if role not in {"agent", "trainer"}:
        raise ValueError("Role must be 'agent' or 'trainer'.")

    password_hash = generate_password_hash(password)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username.strip(), password_hash, role),
        )
        conn.commit()


def get_user(username: str) -> Optional[User]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT username, role FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()

    if row is None:
        return None
    return User(username=row["username"], role=row["role"])


def authenticate(username: str, password: str) -> Optional[User]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT username, password_hash, role FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()

    if row is None:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return User(username=row["username"], role=row["role"])
