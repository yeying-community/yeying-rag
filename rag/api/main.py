# rag/api/main.py
# -*- coding: utf-8 -*-
"""
FastAPI 主应用
- 挂载 memory 路由
- 提供健康检查
"""

from fastapi import FastAPI
from rag.api.deps import get_settings
from rag.api.routers import memory, query, health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 健康检查
    app.include_router(health.router)
    # 挂载路由
    app.include_router(memory.router)
    # app.include_router(debug.router)

    app.include_router(query.router)
    return app


app = create_app()
