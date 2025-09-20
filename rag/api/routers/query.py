# rag/api/routers/query.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

from rag.api.deps import get_embedder, get_weaviate_store
from rag.core.schemas import QueryResponse, QueryRequest,Hit
from rag.llm.providers.openai_client import OpenAIClient
from functools import lru_cache

router = APIRouter()

# 惰性单例，避免 import 时就因环境变量缺失而崩
@lru_cache(maxsize=1)
def get_llm() -> OpenAIClient:
    return OpenAIClient()



@router.post("", response_model=QueryResponse, summary="向量检索 + 基于命中生成答案")
def kb_query(
    req: QueryRequest,
    embedder = Depends(get_embedder),
    llm: OpenAIClient = Depends(get_llm),
):
    if not req.query:
        raise HTTPException(status_code=400, detail="query 不能为空")

    # 1) 向量检索
    qvec = embedder.embed_query(req.query)
    store = get_weaviate_store(req.collection)
    hits = store.search(qvec, top_k=req.top_k)

    # 2) 生成答案（受 max_ctx_chunks 控制）
    contexts = [h["text"] for h in hits[: req.max_ctx_chunks]]
    try:
        answer = llm.rag_answer(question=req.query, contexts=contexts, max_tokens=600)
    except Exception as e:
        # 给调用方一个明确的 502，而不是 500 或空白
        raise HTTPException(status_code=502, detail=f"LLM 生成失败: {e}")

    return QueryResponse(
        collection=store.collection,
        query=req.query,
        top_k=req.top_k,
        hits=hits,
        answer=answer,
    )
