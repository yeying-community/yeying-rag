# -*- coding: utf-8 -*-
"""
Datasource 总入口
- 自动从环境变量读取 SQLite / MinIO / Weaviate 配置
- 聚合 SQLStores, ObjectStores, VectorStores
"""

import os
from typing import Optional

# SQL stores
from rag.datasource.connections.sqlite_connection import SQLiteConnection
from rag.datasource.sqlstores.mem_contexts_store import MemContextsStore
from rag.datasource.sqlstores.mem_primary_store import MemPrimaryStore
from rag.datasource.sqlstores.mem_registry_store import MemRegistryStore
from rag.datasource.sqlstores.mem_deleted_store import MemDeletedStore

# Object store
from rag.datasource.connections.minio_connection import MinioConnection
from rag.datasource.objectstores.minio_store import MinIOStore

# Vector store
from rag.datasource.connections.weaviate_connection import WeaviateConnection
from rag.datasource.vectorstores.weaviate_store import WeaviateStore


class Datasource:
    def __init__(self):
        # ---------- SQLite ----------
        sqlite_path = os.getenv("RAG_DB_PATH", os.path.join(os.getcwd(), "db/rag.sqlite3"))
        self.sqlite_conn = SQLiteConnection(db_path=sqlite_path)
        self.mem_contexts = MemContextsStore(self.sqlite_conn)
        self.mem_primary = MemPrimaryStore(self.sqlite_conn)
        self.mem_registry = MemRegistryStore(self.sqlite_conn)
        self.mem_deleted = MemDeletedStore(self.sqlite_conn)

        # ---------- MinIO ----------
        if os.getenv("MINIO_ENABLED", "false").lower() == "true":
            self.minio_conn = MinioConnection(
                endpoint=os.getenv("MINIO_ENDPOINT"),
                access_key=os.getenv("MINIO_ACCESS_KEY"),
                secret_key=os.getenv("MINIO_SECRET_KEY"),
                secure=os.getenv("MINIO_SECURE", "true").lower() == "true",
            )
            self.minio = MinIOStore(self.minio_conn)
        else:
            self.minio_conn = None
            self.minio = None

        # ---------- Weaviate ----------
        if os.getenv("WEAVIATE_ENABLED", "false").lower() == "true":
            self.weaviate_conn = WeaviateConnection(
                scheme=os.getenv("WEAVIATE_SCHEME", "http"),
                host=os.getenv("WEAVIATE_HOST", "localhost"),
                port=int(os.getenv("WEAVIATE_PORT", "8080")),
                grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
                api_key=os.getenv("WEAVIATE_API_KEY"),
            )
            self.weaviate = WeaviateStore(
                collection=os.getenv("WEAVIATE_COLLECTION", "KbDefault"),
                conn=self.weaviate_conn,
                embedding_dim=int(os.getenv("EMBEDDING_DIM", "0")) or None,
            )

            # 确保辅助记忆的 collection 存在
            from weaviate.classes.config import Property, DataType, Configure
            self.weaviate.ensure_collection(
                name=os.getenv("WEAVIATE_AUX_COLLECTION", "AuxiliaryMemory"),
                properties=[
                    Property(name="text", data_type=DataType.TEXT),
                    Property(name="meta", data_type=DataType.TEXT),
                    Property(name="memory_id", data_type=DataType.TEXT),
                    Property(name="app", data_type=DataType.TEXT),
                    Property(name="url", data_type=DataType.TEXT),
                    Property(name="role", data_type=DataType.TEXT),
                ],
            )
        else:
            self.weaviate_conn = None
            self.weaviate = None

    # ---------- 统一关闭 ----------
    def close(self):
        try:
            self.sqlite_conn.close()
        except Exception:
            pass
        if self.minio_conn:
            try:
                self.minio_conn.close()
            except Exception:
                pass
        if self.weaviate_conn:
            try:
                self.weaviate_conn.close()
            except Exception:
                pass

    def __del__(self):
        self.close()
