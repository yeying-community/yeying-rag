# rag/core/schemas.py
# -*- coding: utf-8 -*-
"""
Pydantic 数据模型 (schemas)
集中定义所有 API 请求 / 响应的 schema
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# ===== 面试官应用（Interviewer 模块） =====
class InterviewQueryReq(BaseModel):
    """面试官场景：生成面试题请求"""
    app: str = "interviewer"
    memory_id: str
    query: str
    company: Optional[str] = None
    target_position: Optional[str] = None
    jd_top_k: int = 3
    memory_top_k: int = 3
    max_chars: int = 500


class InterviewQueryResp(BaseModel):
    """面试官场景：生成面试题响应"""
    app: str = "interviewer"
    questions: List[str]
    context_used: Optional[Dict[str, Any]] = None


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