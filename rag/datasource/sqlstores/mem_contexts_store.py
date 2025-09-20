# -*- coding: utf-8 -*-
"""
MemContextsStore：对 mem_contexts 表的面向业务封装
- create()：插入一条上下文记录（同内容哈希去重）
- get_by_uid() / get_by_hash()：单条查询
- list_by_memory() / list_by_app()：分页列表
- bump_qa()：累加 QA 计数
- mark_summarized()：标记已摘要
- update_desc()：更新描述
"""
from __future__ import annotations
import sqlite3
from typing import Optional, List, Dict, Any
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]

class MemContextsStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    # ---------- 基础查询 ----------
    def get_by_uid(self, uid: str) -> Optional[Row]:
        return self.conn.query_one("SELECT * FROM mem_contexts WHERE uid = ?", (uid,))

    def get_by_hash(self, content_sha256: str) -> Optional[Row]:
        return self.conn.query_one("SELECT * FROM mem_contexts WHERE content_sha256 = ?", (content_sha256,))

    # ---------- 列表 ----------
    def list_by_memory(self, memory_id: str, limit: int = 20, offset: int = 0) -> List[Row]:
        sql = """
        SELECT * FROM mem_contexts
         WHERE memory_id = ?
         ORDER BY created_at DESC
         LIMIT ? OFFSET ?
        """
        return self.conn.query_all(sql, (memory_id, limit, offset))

    def list_by_app(self, app: str, limit: int = 20, offset: int = 0) -> List[Row]:
        sql = """
        SELECT * FROM mem_contexts
         WHERE app = ?
         ORDER BY created_at DESC
         LIMIT ? OFFSET ?
        """
        return self.conn.query_all(sql, (app, limit, offset))

    # ---------- 新增（带哈希幂等） ----------
    def create(
        self,
        uid: str,
        memory_id: str,
        app: str,
        url: str,
        content_sha256: str,
        description: Optional[str] = None,
    ) -> Row:
        """
        插入一条上下文：
        - 若 content_sha256 已存在（你表上是 UNIQUE），则返回已有记录（幂等）
        - 否则插入新纪录
        """
        try:
            self.conn.execute(
                """
                INSERT INTO mem_contexts(uid, memory_id, app, description, url, content_sha256)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (uid, memory_id, app, description, url, content_sha256),
            )
        except sqlite3.IntegrityError:
            # 命中 UNIQUE(content_sha256)，返回已有记录
            existed = self.get_by_hash(content_sha256)
            if existed:
                return existed
            # 也可能是主键 uid 冲突，这里兜底取 uid
            existed = self.get_by_uid(uid)
            if existed:
                return existed
            raise  # 其它约束错误，继续抛出

        # 返回刚插入的完整行
        return self.get_by_uid(uid)  # type: ignore[return-value]

    # ---------- 计数与状态 ----------
    def bump_qa(self, uid: str, delta: int = 1) -> None:
        """
        QA 计数累加；同时刷新 updated_at
        """
        self.conn.execute(
            """
            UPDATE mem_contexts
               SET qa_count = qa_count + ?,
                   updated_at = datetime('now')
             WHERE uid = ?
            """,
            (delta, uid),
        )

    def mark_summarized(self, uid: str, summarized_at: Optional[str] = None) -> None:
        """
        标记该上下文已被摘要；summarized_at 可传入外部时间戳（ISO8601），
        不传则使用 SQLite 当前时间。
        """
        if summarized_at:
            self.conn.execute(
                """
                UPDATE mem_contexts
                   SET is_summarized = 1,
                       summarized_at = ?,
                       updated_at = datetime('now')
                 WHERE uid = ?
                """,
                (summarized_at, uid),
            )
        else:
            self.conn.execute(
                """
                UPDATE mem_contexts
                   SET is_summarized = 1,
                       summarized_at = datetime('now'),
                       updated_at = datetime('now')
                 WHERE uid = ?
                """,
                (uid,),
            )


    def update_desc(self, uid: str, description: Optional[str]) -> None:
        self.conn.execute(
            """
            UPDATE mem_contexts
               SET description = ?,
                   updated_at = datetime('now')
             WHERE uid = ?
            """,
            (description, uid),
        )
