# rag/core/schemas.py
# -*- coding: utf-8 -*-
"""
Pydantic 数据模型 (schemas)
集中定义所有 API 请求 / 响应的 schema
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel


# ===== Memory 模块 =====
class CreateReq(BaseModel):
    app: str
    params: Optional[Dict[str, Any]] = None


class CreateResp(BaseModel):
    memory_id: str


class PushReq(BaseModel):
    memory_id: str
    app: str
    url: str
    description: Optional[str] = None


class PushResp(BaseModel):
    status: str = "ok"
    row: Dict[str, Any]


class QueryReq(BaseModel):
    memory_id: str
    app: str
    query: str


class QueryResp(BaseModel):
    answer: str
    context_used: Dict[str, Any]


class DeleteReq(BaseModel):
    memory_id: str
    app: str
    url: str


class DeleteResp(BaseModel):
    status: str = "deleted"


class ClearReq(BaseModel):
    memory_id: str
    app: str


class ClearResp(BaseModel):
    deleted: int


# ===== 可选通用模型 =====
class ErrorResp(BaseModel):
    detail: str



####################################
class JDItem(BaseModel):
    job_id: str
    company: str
    hash: Optional[str] = None
    position: str
    category: List[str] = []
    department: Optional[str] = None
    product: Optional[str] = None
    location: List[str] = []
    education: Optional[str] = None
    experience: Optional[str] = None
    requirements: str
    description: str
    extra: Dict[str, Optional[str]] = {}