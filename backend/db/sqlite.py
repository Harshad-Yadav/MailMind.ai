from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.core.config import get_settings


def initialize_database() -> None:
    settings = get_settings()
    db_path = Path(settings.sqlite_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                email_id TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id TEXT NOT NULL,
                reward REAL NOT NULL,
                done INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.commit()


def persist_episode(episode_id: str, task_id: str, email_id: str, state: dict[str, Any]) -> None:
    try:
        settings = get_settings()
        initialize_database()
        with sqlite3.connect(settings.sqlite_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO episodes (episode_id, task_id, email_id, state_json)
                VALUES (?, ?, ?, ?)
                """,
                (episode_id, task_id, email_id, json.dumps(state)),
            )
            connection.commit()
    except Exception as e:
        print(f"WARN: Failed to persist episode telemetry to SQLite: {e}")


def persist_step(episode_id: str, reward: float, done: bool, payload: dict[str, Any]) -> None:
    try:
        settings = get_settings()
        initialize_database()
        with sqlite3.connect(settings.sqlite_path) as connection:
            connection.execute(
                """
                INSERT INTO steps (episode_id, reward, done, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (episode_id, reward, int(done), json.dumps(payload)),
            )
            connection.commit()
    except Exception as e:
        print(f"WARN: Failed to persist step telemetry to SQLite: {e}")
