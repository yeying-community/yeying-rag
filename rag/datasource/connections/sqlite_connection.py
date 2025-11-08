# -*- coding: utf-8 -*-
"""
SQLiteConnection
- 单例/线程安全封装
- 自动创建 db 目录
- 初始化表结构（mem_contexts, mem_primary）
- 提供 execute/query_all/query_one 等基础操作
"""
from __future__ import annotations
import os, sqlite3, threading
from pathlib import Path
from typing import Any, Iterable, Optional

# ---------- 表定义 ----------
DDL = r"""
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

-- 记忆注册表：登记 memory_id ↔ 应用/参数
CREATE TABLE IF NOT EXISTS mem_registry (
  memory_id    TEXT PRIMARY KEY,
  app          TEXT NOT NULL,                     -- 所属应用：interviewer / grader / dev ...
  name         TEXT,                              -- 可选：记忆别名
  owner        TEXT,                              -- 可选：创建者/归属人
  params_json  TEXT,                              -- 主/辅记忆配置参数
  status       TEXT NOT NULL DEFAULT 'active',    -- active / archived / disabled
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mem_registry_app_created
  ON mem_registry (app, created_at DESC);

-- 删除清单（逻辑删除，不直接物理删除 MinIO 对象）
CREATE TABLE IF NOT EXISTS mem_deleted (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  memory_id  TEXT NOT NULL,
  key        TEXT NOT NULL,          -- MinIO 对象 key
  deleted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mem_deleted_memory ON mem_deleted(memory_id);
CREATE INDEX IF NOT EXISTS idx_mem_deleted_key ON mem_deleted(key);

-- 会话上下文目录（每次会话一个文件）
CREATE TABLE IF NOT EXISTS mem_contexts (
  uid            TEXT PRIMARY KEY,                 -- UUID
  memory_id      TEXT NOT NULL,
  app            TEXT NOT NULL,
  description    TEXT,
  url            TEXT NOT NULL,                    -- MinIO 对象 key 或 s3://bucket/key
  content_sha256 TEXT NOT NULL UNIQUE,             -- 内容哈希（幂等）
  qa_count       INTEGER NOT NULL DEFAULT 0,
  is_summarized  INTEGER NOT NULL DEFAULT 0,       -- 0/1
  summarized_at  TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mem_contexts_memory_created
  ON mem_contexts (memory_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mem_contexts_app_created
  ON mem_contexts (app, created_at DESC);

-- 主记忆（每个 memory_id 一行，维护累计与摘要指针）
CREATE TABLE IF NOT EXISTS mem_primary (
  memory_id          TEXT PRIMARY KEY,
  summary_url        TEXT,
  summary_version    INTEGER NOT NULL DEFAULT 0,
  recent_qa_count    INTEGER NOT NULL DEFAULT 0,   -- 保留的“未摘要”尾部 QA 数
  total_qa_count     INTEGER NOT NULL DEFAULT 0,   -- 累计 QA
  last_summary_index INTEGER NOT NULL DEFAULT 0,   -- 已摘要到的 QA 索引（0..n）
  last_summary_at    TEXT,
  created_at         TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_uploaded_jd (
  jd_id       TEXT PRIMARY KEY,                -- JD 唯一标识 UUID
  memory_id   TEXT NOT NULL,                   -- 所属会话或用户ID
  company     TEXT,                            -- 公司名称（可选）
  position    TEXT,                            -- 职位名称（可选）
  content     TEXT NOT NULL,                   -- JD原文（文本或JSON）
  uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_user_uploaded_jd_memory
  ON user_uploaded_jd (memory_id, uploaded_at DESC);
"""

# ---------- SQLite 封装 ----------
class SQLiteConnection:
    def __init__(self, db_path: Optional[str] = None) -> None:
        # 默认路径：项目根目录/db/rag.sqlite3
        default_path = Path(os.getcwd()) / "db" / "rag.sqlite3"
        self.db_path = Path(db_path or os.getenv("RAG_DB_PATH", default_path))

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 连接数据库（允许多线程复用）
        self._conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

        # 初始化表结构
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(DDL)

    # ---------- 基础执行 ----------
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock, self._conn:
            cur = self._conn.execute(sql, params)
            return cur

    def query_all(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
