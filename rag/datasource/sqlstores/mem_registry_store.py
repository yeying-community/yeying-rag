# -*- coding: utf-8 -*-
"""
MemRegistryStore: 管理 mem_registry（记忆注册表）
- upsert()：注册/更新 memory_id
- get()：按 memory_id 获取
- list_by_app()：按 app 列出
- set_status()：修改状态（active/archived/disabled）
- update_params()：更新参数 JSON
"""
from __future__ import annotations
from typing import Optional, Dict, Any, List
import json

from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]

class MemRegistryStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(
        self,
        memory_id: str,
        app: str,
        params: Optional[dict] = None,
        name: Optional[str] = None,
        owner: Optional[str] = None,
        status: str = "active",
    ) -> None:
        params_json = json.dumps(params or {}, ensure_ascii=False)
        self.conn.execute(
            """
            INSERT INTO mem_registry(memory_id, app, name, owner, params_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
              app         = excluded.app,
              name        = excluded.name,
              owner       = excluded.owner,
              params_json = excluded.params_json,
              status      = excluded.status,
              updated_at  = datetime('now')
            """,
            (memory_id, app, name, owner, params_json, status),
        )

    def get(self, memory_id: str) -> Optional[Row]:
        return self.conn.query_one("SELECT * FROM mem_registry WHERE memory_id = ?", (memory_id,))

    def list_by_app(self, app: str, limit: int = 50, offset: int = 0) -> List[Row]:
        return self.conn.query_all(
            """
            SELECT * FROM mem_registry
             WHERE app = ?
             ORDER BY created_at DESC
             LIMIT ? OFFSET ?
            """,
            (app, limit, offset),
        )

    def set_status(self, memory_id: str, status: str) -> None:
        self.conn.execute(
            """
            UPDATE mem_registry
               SET status = ?,
                   updated_at = datetime('now')
             WHERE memory_id = ?
            """,
            (status, memory_id),
        )

    def update_params(self, memory_id: str, params: dict) -> None:
        params_json = json.dumps(params or {}, ensure_ascii=False)
        self.conn.execute(
            """
            UPDATE mem_registry
               SET params_json = ?,
                   updated_at   = datetime('now')
             WHERE memory_id = ?
            """,
            (params_json, memory_id),
        )
