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

    # Feature toggle
    weaviate_enabled: bool = os.getenv("WEAVIATE_ENABLED", "false").lower() == "true"
    minio_enabled: bool = os.getenv("MINIO_ENABLED", "false").lower() == "true"

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
