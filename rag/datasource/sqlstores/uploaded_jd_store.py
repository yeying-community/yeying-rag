# -*- coding: utf-8 -*-
"""
用户上传 JD 存储表
"""

import datetime
from typing import Optional
from uuid import uuid4

class UploadedJDStore:
    def __init__(self, sqlite_conn):
        self.conn = sqlite_conn
        self._ensure_table()

    def _ensure_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS user_uploaded_jd (
            jd_id TEXT PRIMARY KEY,
            memory_id TEXT NOT NULL,
            company TEXT,
            position TEXT,
            content TEXT NOT NULL,
            uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """)

    def insert(self, memory_id: str, company: Optional[str], position: Optional[str], content: str) -> str:
        jd_id = str(uuid4())
        now = datetime.datetime.utcnow().isoformat()
        self.conn.execute(
            """
            INSERT INTO user_uploaded_jd (jd_id, memory_id, company, position, content, uploaded_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (jd_id, memory_id, company, position, content, now, now)
        )
        return jd_id

    def get(self, jd_id: str, memory_id: str):
        return self.conn.query_one(
            "SELECT company, position, content FROM user_uploaded_jd WHERE jd_id=? AND memory_id=?",
            (jd_id, memory_id)
        )
