# -*- coding: utf-8 -*-
"""
MemPrimaryStore：管理主记忆的摘要进度
- upsert()：初始化或更新一条 memory_id 的状态
- bump_total()：累加总问答数
- update_summary()：写入新的摘要（URL + version + 时间）
- advance_index()：推进“已摘要到第几条 QA”
- get()：按 memory_id 获取
"""
from __future__ import annotations
from typing import Optional, Dict, Any
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]

class MemPrimaryStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def get(self, memory_id: str) -> Optional[Row]:
        return self.conn.query_one("SELECT * FROM mem_primary WHERE memory_id = ?", (memory_id,))

    def upsert(self, memory_id: str) -> None:
        """
        如果不存在则插入一行；存在则更新时间戳
        """
        self.conn.execute(
            """
            INSERT INTO mem_primary(memory_id)
            VALUES (?)
            ON CONFLICT(memory_id) DO UPDATE SET
              updated_at = datetime('now')
            """,
            (memory_id,),
        )

    def bump_total(self, memory_id: str, delta: int = 1) -> None:
        """
        累加总问答数；同时 recent_qa_count 也 +delta
        """
        self.conn.execute(
            """
            UPDATE mem_primary
               SET total_qa_count = total_qa_count + ?,
                   recent_qa_count = recent_qa_count + ?,
                   updated_at = datetime('now')
             WHERE memory_id = ?
            """,
            (delta, delta, memory_id),
        )

    def update_summary(self, memory_id: str, summary_url: str) -> None:
        """
        写入摘要文件 URL，并提升版本号
        """
        self.conn.execute(
            """
            UPDATE mem_primary
               SET summary_url = ?,
                   summary_version = summary_version + 1,
                   last_summary_at = datetime('now'),
                   recent_qa_count = 0,
                   updated_at = datetime('now')
             WHERE memory_id = ?
            """,
            (summary_url, memory_id),
        )

    def advance_index(self, memory_id: str, new_index: int) -> None:
        """
        把“已摘要到的 QA 索引”推进到 new_index
        """
        self.conn.execute(
            """
            UPDATE mem_primary
               SET last_summary_index = ?,
                   updated_at = datetime('now')
             WHERE memory_id = ?
            """,
            (new_index, memory_id),
        )
