# rag/api/routers/memory.py
# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends

from rag.api.deps import get_memory_manager, get_llm, get_datasource
from rag.core.pipeline import RAGPipeline
from rag.memory.memory_manager import MemoryManager
from rag.llm.providers.openai_client import OpenAIClient
from rag.core.schemas import (
    CreateReq, CreateResp,
    PushReq, PushResp,
    QueryReq, QueryResp,
    DeleteReq, DeleteResp,
    ClearReq, ClearResp,
)

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.post("/create", response_model=CreateResp)
def create_memory(req: CreateReq, memory: MemoryManager = Depends(get_memory_manager)):
    memory_id = memory.create_memory(req.app, req.params)
    return {"memory_id": memory_id}


@router.post("/push", response_model=PushResp)
def push_message(req: PushReq, memory: MemoryManager = Depends(get_memory_manager)):
    row = memory.push_message(req.memory_id, req.app, req.url, req.description)
    return {"status": "ok", "row": row}


@router.post("/query", response_model=QueryResp)
def query_memory(
    req: QueryReq,
    memory: MemoryManager = Depends(get_memory_manager),
    llm: OpenAIClient = Depends(get_llm),
    ds=Depends(get_datasource),
):
    pipeline = RAGPipeline(ds, memory, llm)
    result = pipeline.run(req.memory_id, req.app, req.query)
    return result


@router.post("/delete", response_model=DeleteResp)
def delete_message(req: DeleteReq, memory: MemoryManager = Depends(get_memory_manager)):
    memory.delete_message(req.memory_id, req.app, req.url)
    return {"status": "deleted"}


@router.post("/clear", response_model=ClearResp)
def clear_memory(req: ClearReq, memory: MemoryManager = Depends(get_memory_manager)):
    deleted = memory.clear_memory(req.memory_id, req.app)
    return {"deleted": deleted}
