# 知识库上传/重建索引/删除/统计
# rag/api/routers/kb.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from rag.core.schemas import UpsertRequest, UpsertResponse, UploadTextResponse
from rag.api.deps import get_embedder, get_weaviate_store
from rag.utils.text_splitter import simple_split
router = APIRouter()



@router.post("/upload", response_model=UpsertResponse, summary="上传文本并入库（进入向量数据库）")
def kb_upload(req: UpsertRequest, embedder=Depends(get_embedder)):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts 不能为空")
    vectors = embedder.embed_documents(req.texts)
    store = get_weaviate_store(req.collection)
    ids = store.add_texts(req.texts, vectors, req.metadatas)
    return UpsertResponse(collection=store.collection, count=len(ids), ids=ids)


@router.post("/upload_file", summary="上传可编辑文本（.md/.txt）→ 切分 → 入库")
async def kb_upload_text(
    file: UploadFile = File(...),
    collection: Optional[str] = Form(None),
    chunk_size: int = Form(1024),
    overlap: int = Form(150),
    embedder = Depends(get_embedder),
):
    # 1) 校验扩展名
    name = (file.filename or "upload.txt").strip()
    lower = name.lower()
    if not (lower.endswith(".md") or lower.endswith(".txt")):
        raise HTTPException(status_code=415, detail="仅支持 .md / .txt")

    # 2) 读取并解码为 utf-8 文本（忽略无法解码字符）
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="ignore")

    # 简单规范化换行，去掉 BOM
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件为空或无可用文本")

    # 3) 切分
    chunks = simple_split(text, chunk_size=chunk_size, overlap=overlap)
    chunk_texts = [c["text"] for c in chunks]
    metadatas = [{
        "filename": name,
        "ext": ".md" if lower.endswith(".md") else ".txt",
        "chunk_index": i,
        "start": c["start"],
        "end": c["end"],
    } for i, c in enumerate(chunks)]

    # 4) 嵌入 & 入库
    vectors = embedder.embed_documents(chunk_texts)
    store = get_weaviate_store(collection)
    ids = store.add_texts(chunk_texts, vectors, metadatas)

    return {
        "collection": store.collection,
        "filename": name,
        "chunks": len(ids),
        "ids": ids[:10],  # 返回前 10 个以免响应过大
    }