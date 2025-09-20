# -*- coding: utf-8 -*-
"""
MemDeletedStore: 管理逻辑删除的对话文件
- mark_deleted(): 标记某个 key 已删除
- list_deleted(): 按 memory_id 列出所有已删除对象
- is_deleted(): 判断某个 key 是否被标记删除
"""
from __future__ import annotations
from typing import List, Dict
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, any]

class MemDeletedStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def mark_deleted(self, memory_id: str, key: str) -> None:
        self.conn.execute(
            "INSERT INTO mem_deleted (memory_id, key) VALUES (?, ?)",
            (memory_id, key),
        )

    def list_deleted(self, memory_id: str) -> List[Row]:
        return self.conn.query_all(
            "SELECT * FROM mem_deleted WHERE memory_id = ? ORDER BY deleted_at DESC",
            (memory_id,),
        )

    def is_deleted(self, key: str) -> bool:
        row = self.conn.query_one(
            "SELECT 1 FROM mem_deleted WHERE key = ?",
            (key,),
        )
        return row is not None
