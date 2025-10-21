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
    service_name: str = os.getenv("SERVICE_NAME", "yeying-rag")
    service_version: str = os.getenv("SERVICE_VERSION", "0.1.0")
    rag_env: str = os.getenv("RAG_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Weaviate 配置
    weaviate_enabled: bool = os.getenv("WEAVIATE_ENABLED", "false").lower() == "true"
    weaviate_scheme: str = os.getenv("WEAVIATE_SCHEME", "http")
    weaviate_host: str = os.getenv("WEAVIATE_HOST", "localhost")
    weaviate_port: int = int(os.getenv("WEAVIATE_PORT", 8080))
    weaviate_grpc_port: int = int(os.getenv("WEAVIATE_GRPC_PORT", 50051))

    # MinIO 配置
    minio_enabled: bool = os.getenv("MINIO_ENABLED", "false").lower() == "true"
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # LLM 配置
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


from rag.llm.embeddings.openai_embedding import OpenAIEmbedder

@lru_cache(maxsize=32)
def get_embedder() -> OpenAIEmbedder:
    return OpenAIEmbedder()

# 单例 Settings
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

# ===== Datasource =====
from rag.datasource.base import Datasource

@lru_cache(maxsize=1)
def get_datasource() -> Datasource:
    s = get_settings()
    ds = Datasource()

    # 如果服务被禁用，可以在这里直接报错
    if s.weaviate_enabled is False and ds.weaviate is None:
        raise HTTPException(status_code=503, detail="Weaviate disabled (WEAVIATE_ENABLED=false)")
    if s.minio_enabled is False and ds.minio is None:
        raise HTTPException(status_code=503, detail="Minio disabled (MINIO_ENABLED=false)")

    return ds

# ===== MemoryManager =====
from rag.memory.memory_manager import MemoryManager

@lru_cache(maxsize=32)
def get_memory_manager() -> MemoryManager:
    ds = get_datasource()
    embedder = get_embedder()
    return MemoryManager(ds, embedder=embedder)

# ===== LLM Client =====
from rag.llm.providers.openai_client import OpenAIClient

@lru_cache(maxsize=32)
def get_llm() -> OpenAIClient:
    s = get_settings()
    return OpenAIClient(
        model=s.openai_model,
        api_base=s.openai_api_base,
        api_key=s.openai_api_key,
    )
