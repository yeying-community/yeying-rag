# 统一数据模型
# rag/core/schemas.py
# -*- coding: utf-8 -*-
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ===== KB / 向量入库 =====
class UpsertRequest(BaseModel):
    """上传已切分的文本片段并入库（BYOV）。"""
    collection: Optional[str] = Field(
        default=None, description="集合名；不传则用环境变量默认值"
    )
    texts: List[str] = Field(
        ..., description="要写入的文本片段（已切分）"
    )
    metadatas: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="与 texts 对应的元数据"
    )

class UpsertResponse(BaseModel):
    collection: str
    count: int
    ids: List[str]


# ===== 仅用于 .md/.txt 文件上传后的结果回执 =====
class UploadTextResponse(BaseModel):
    collection: str
    filename: str
    chunks: int
    ids: List[str]


# ===== 查询（向量检索 + 可选生成答案）=====
class Hit(BaseModel):
    id: str = Field(..., description="Weaviate 对象 UUID")
    distance: float = Field(..., ge=0, description="向量距离（越小越相似）")
    text: str = Field(..., description="命中的文本片段")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="写入时携带的元数据")

class QueryRequest(BaseModel):
    collection: Optional[str] = Field(
        default=None, description="集合名；不传则用环境变量默认值"
    )
    query: str = Field(..., description="查询问题")
    top_k: int = Field(default=5, ge=1, le=50, description="向量检索返回条数")
    max_ctx_chunks: int = Field(
        default=5, ge=1, le=20, description="用于生成答案的上下文片段上限"
    )
    return_answer: bool = Field(
        default=True, description="是否在检索结果基础上调用 LLM 生成答案"
    )

class QueryResponse(BaseModel):
    collection: str
    query: str
    top_k: int
    hits: List[Hit]
    answer: Optional[str] = Field(default=None, description="基于命中生成的答案；未生成则为 null")


# ===== 维护类接口（可选）=====
class DeleteCollectionRequest(BaseModel):
    collection: str

class DeleteCollectionResponse(BaseModel):
    collection: str
    deleted: bool


# ===== 健康检查（可按需使用）=====
class HealthzResponse(BaseModel):
    status: str
    version: Optional[str] = None