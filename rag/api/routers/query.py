# -*- coding: utf-8 -*-
"""
RAG 通用查询接口（支持面试官模式）
------------------------------------------------
- 默认模式：结合记忆进行问答（调用 pipeline.run）
- 面试官模式：结合 JD + 记忆生成面试题（调用 pipeline.generate_interview_questions）
"""
from typing import Optional, Union
from fastapi import APIRouter, HTTPException, Body, Depends
from functools import lru_cache

# 依赖与核心组件
from rag.api.deps import get_memory_manager, get_datasource
from rag.llm.providers.openai_client import OpenAIClient
from rag.core.pipeline import RAGPipeline
from rag.core.schemas import (
    QueryReq,
    QueryResp,
    InterviewQueryReq,
    InterviewQueryResp, UploadJDReq,
)

router = APIRouter()


# ---------- 单例缓存 ----------
@lru_cache(maxsize=1)
def get_llm() -> OpenAIClient:
    """缓存 LLM 实例，避免重复初始化"""
    return OpenAIClient()


# ---------- RAG 主接口 ----------
@router.post(
    "/query",
    summary="RAG 查询接口（支持问答与面试题生成）",
    response_model=Union[QueryResp, InterviewQueryResp],
)
def query_rag(
    req: Union[QueryReq, InterviewQueryReq] = Body(...),
    ds=Depends(get_datasource),
    memory=Depends(get_memory_manager),
    llm: OpenAIClient = Depends(get_llm),
):
    """
    通用 RAG 查询接口
    -----------------------------
    - app=default → 普通问答
    - app=interviewer → 生成面试题（只输出问题，不输出答案）
    """


    pipeline = RAGPipeline(ds=ds, memory=memory, llm=llm)

    try:
        # interviewer 模式：生成面试题
        if req.app.lower() == "interviewer":
            if not req.resume_url:
                raise HTTPException(status_code=400, detail="resume_url 不能为空")
            result = pipeline.generate_interview_questions(
                memory_id=req.memory_id,
                app=req.app,
                resume_url=getattr(req, "resume_url", None),
                jd_id=getattr(req, "jd_id", None),
                company=getattr(req, "company", None),
                target_position=getattr(req, "target_position", None),
                jd_top_k=getattr(req, "jd_top_k", 3),
                memory_top_k=getattr(req, "memory_top_k", 3),
                max_chars=getattr(req, "max_chars", 4000),
            )
            return InterviewQueryResp(
                app="interviewer",
                questions=result["questions"],
                context_used=result.get("context_used"),
            )

        # 默认模式：普通问答
        else:
            if not req.query:
                raise HTTPException(status_code=400, detail="query 不能为空")
            result = pipeline.run(
                memory_id=req.memory_id,
                app=req.app,
                query=getattr(req, "query", None),
                summary_k=getattr(req, "summary_k", 1),
                recent_k=getattr(req, "recent_k", 6),
                aux_top_k=getattr(req, "aux_top_k", 5),
                max_chars=getattr(req, "max_chars", 4000),
            )
            return QueryResp(
                answer=result["answer"],
                context_used=result.get("context_used"),
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 执行失败: {e}")

from pydantic import BaseModel
import uuid, datetime

# ---------- 上传JD接口 ----------
@router.post(
    "/query/uploadJD",
    summary="面试官上传自定义JD（仅 interviewer 模式可用）",
)
def upload_jd_json(
    req: UploadJDReq,
    ds=Depends(get_datasource),
):
    """
    上传自定义 JD，只有 app='interviewer' 时才允许写入数据库。
    要求 memory_id 必须已在 mem_registry 表注册。
    """
    # 1️⃣ 验证 app 类型
    if req.app.lower() != "interviewer":
        raise HTTPException(status_code=403, detail="仅 interviewer 模式允许上传 JD")

    # 2️⃣ 验证 memory_id 是否存在且归属 interviewer
    mem_row = ds.mem_registry.get(req.memory_id)
    if not mem_row or mem_row.get("app") != "interviewer":
        raise HTTPException(status_code=404, detail=f"未找到对应的 interviewer memory_id: {req.memory_id}")

    # 3️⃣ 插入 JD 记录
    try:
        jd_id = ds.uploaded_jd.insert(
            memory_id=req.memory_id,
            company=req.company,
            position=req.position,
            content=req.content
        )
        return {"jd_id": jd_id, "message": "JD 上传成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD 上传失败: {e}")