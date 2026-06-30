"""
Управление SQLite базой данных для хранения диалогов.
"""

import sqlite3
import json
import uuid
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime


class Database:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        """Создать таблицы, если они не существуют."""
        conn = self._get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                profile_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id);
        """)
        conn.commit()

    # --- Конверсации ---

    def create_conversation(self, title: str = "Новый диалог", profile_id: Optional[str] = None) -> str:
        """Создать новую конверсацию. Возвращает ID."""
        now = datetime.now().isoformat()
        conv_id = str(uuid.uuid4())[:8]
        conn = self._get_connection()
        conn.execute(
            "INSERT INTO conversations (id, title, profile_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, title, profile_id, now, now),
        )
        conn.commit()
        return conv_id

    def get_conversations(self) -> list:
        """Получить все конверсации, отсортированные по дате обновления."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        """Получить одну конверсацию."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conv_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_conversation_title(self, conv_id: str, title: str):
        """Обновить название конверсации."""
        now = datetime.now().isoformat()
        conn = self._get_connection()
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, conv_id),
        )
        conn.commit()

    def delete_conversation(self, conv_id: str):
        """Удалить конверсацию и все её сообщения."""
        conn = self._get_connection()
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()

    # --- Сообщения ---

    def add_message(self, conversation_id: str, role: str, content: str) -> str:
        """Добавить сообщение. Возвращает ID сообщения."""
        now = datetime.now().isoformat()
        msg_id = str(uuid.uuid4())[:8]
        conn = self._get_connection()
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, conversation_id, role, content, now),
        )
        # Обновить время конверсации
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        conn.commit()
        return msg_id

    def get_messages(self, conversation_id: str) -> list:
        """Получить все сообщения конверсации по порядку."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        """Закрыть соединение."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
