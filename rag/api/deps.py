# rag/api/deps.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import HTTPException

# ===== 只加载一次 .env =====
load_dotenv(override=False)

# ===== Settings =====
class Settings(BaseModel):
    # Service
    service_name: str = os.getenv("SERVICE_NAME", "yeying-rag")
    service_version: str = os.getenv("SERVICE_VERSION", "0.1.0")
    rag_env: str = os.getenv("RAG_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Weaviate
    weaviate_enabled: bool = os.getenv("WEAVIATE_ENABLED", "false").lower() == "true"
    weaviate_scheme: str = os.getenv("WEAVIATE_SCHEME", "http")
    weaviate_host: str = os.getenv("WEAVIATE_HOST", "localhost")
    weaviate_port: int = int(os.getenv("WEAVIATE_PORT", "8080"))
    weaviate_grpc_port: int = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
    weaviate_api_key: Optional[str] = os.getenv("WEAVIATE_API_KEY") or None
    weaviate_collection: str = os.getenv("WEAVIATE_COLLECTION", "KbDefault")

    # Embedding（用于校验维度，可选）
    embedding_dim: Optional[int] = (
        int(os.getenv("EMBEDDING_DIM")) if os.getenv("EMBEDDING_DIM") else None
    )

    # OpenAI / 兼容 Ark(方舟) 网关
    openai_api_base: str = os.getenv("EMBED_API_BASE", "https://api.openai.com/v1")
    openai_api_key: Optional[str] = os.getenv("EMBED_API_KEY") or None
    openai_embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    # MinIO（可选）
    minio_enabled: bool = os.getenv("MINIO_ENABLED", "false").lower() == "true"
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    minio_bucket_kb: str = os.getenv("MINIO_BUCKET_KB", "yeying-kb")
    minio_bucket_memory: str = os.getenv("MINIO_BUCKET_MEMORY", "yeying-memory")


# 单例 Settings
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# ===== 依赖工厂 =====
# Weaviate 连接（可在路由中做健康检测或直接给 Store 用）
from rag.datasource.connections.weaviate_connection import WeaviateConnection

@lru_cache(maxsize=1)
def get_weaviate_connection() -> WeaviateConnection:
    s = get_settings()
    if not s.weaviate_enabled:
        raise HTTPException(status_code=503, detail="Weaviate disabled (WEAVIATE_ENABLED=false)")
    return WeaviateConnection(
        scheme=s.weaviate_scheme,
        host=s.weaviate_host,
        port=s.weaviate_port,
        grpc_port=s.weaviate_grpc_port,
        api_key=s.weaviate_api_key,
    )


# Weaviate Store（默认使用 env 中的集合名；也可在路由中传自定义集合）
from rag.datasource.vectorstores.weaviate_store import WeaviateStore

def get_weaviate_store(collection: Optional[str] = None) -> WeaviateStore:
    s = get_settings()
    if not s.weaviate_enabled:
        raise HTTPException(status_code=503, detail="Weaviate disabled (WEAVIATE_ENABLED=false)")
    col = collection or s.weaviate_collection
    # 这里不强制复用连接实例（WeaviateStore 内部已缓存/轻量），保持简单
    return WeaviateStore(collection=col, embedding_dim=s.embedding_dim)


# Embedder（当前用 OpenAI 兼容接口；可指向 Ark/Doubao）
from rag.llm.embeddings.openai_embedding import OpenAIEmbedder

@lru_cache(maxsize=1)
def get_embedder() -> OpenAIEmbedder:
    s = get_settings()
    # OpenAIEmbedder 内部会读 OPENAI_API_BASE / OPENAI_API_KEY / OPENAI_EMBED_MODEL
    # 这里做最小化校验（可选）
    if not s.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    return OpenAIEmbedder()


# MinIO Store（如果你已有 minio_store.py，这里暴露一个工厂；没有则可忽略）
try:
    from rag.datasource.objectstores.minio_store import MinIOStore  # 可选依赖
except Exception:
    MinIOStore = None  # type: ignore

def get_minio_store() -> Optional["MinIOStore"]:
    s = get_settings()
    if not s.minio_enabled or MinIOStore is None:
        return None
    return MinIOStore(
        endpoint=s.minio_endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=s.minio_secure,
    )
