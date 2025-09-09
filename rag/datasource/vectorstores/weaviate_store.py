# rag/datasource/vectorstores/weaviate_store.py
# -*- coding: utf-8 -*-
import os
import json
from typing import List, Dict, Any, Optional

import weaviate
import weaviate.classes.config as wc
import weaviate.classes.query as wq
from weaviate.exceptions import UnexpectedStatusCodeError

from rag.datasource.connections.weaviate_connection import WeaviateConnection


def _norm_class(name: str) -> str:
    s = "".join(ch for ch in name if ch.isalnum()) or "C"
    if not s[0].isalpha():
        s = "C" + s
    return s[0].upper() + s[1:]


def _env_int(key: str, default: Optional[int]) -> Optional[int]:
    v = os.getenv(key)
    if not v:
        return default
    try:
        return int(v)
    except ValueError:
        return default


class WeaviateStore:
    """
    最小可用版（只适配当前 weaviate-client v4 行为）：
    - BYOV（自带向量）
    - 仅实现 add_texts / search 两个方法
    - add_object 返回 uuid.UUID → 用 str(r)
    - 不做多版本兼容分支
    """

    def __init__(
        self,
        collection: Optional[str] = None,
        conn: Optional[WeaviateConnection] = None,
        embedding_dim: Optional[int] = None,  # 可选校验
    ):
        self.collection = _norm_class(collection or os.getenv("WEAVIATE_COLLECTION", "KbDefault"))
        self.embedding_dim = embedding_dim or _env_int("EMBEDDING_DIM", None)

        if conn is None:
            scheme = os.getenv("WEAVIATE_SCHEME", "http")
            host = os.getenv("WEAVIATE_HOST", "localhost")
            port = _env_int("WEAVIATE_PORT", 8080) or 8080
            grpc_port = _env_int("WEAVIATE_GRPC_PORT", 50051) or 50051
            api_key = os.getenv("WEAVIATE_API_KEY") or None
            conn = WeaviateConnection(scheme, host, port, grpc_port, api_key)

        self._conn = conn
        self.client: weaviate.WeaviateClient = self._conn.client

        self._ensure_collection()

    # ---------- schema（幂等但超简单） ----------
    def _ensure_collection(self) -> None:
        # 先试图获取，存在就返回；不存在则创建
        try:
            self.client.collections.get(self.collection)
            return
        except Exception:
            pass

        try:
            self.client.collections.create(
                name=self.collection,
                properties=[
                    wc.Property(name="text", data_type=wc.DataType.TEXT),
                    wc.Property(name="meta", data_type=wc.DataType.TEXT),  # 存 JSON 字符串
                ],
                vector_config=wc.Configure.Vectors.self_provided(),       # BYOV
            )
        except UnexpectedStatusCodeError as e:
            # 已存在（422/409）时直接忽略，保证幂等
            if "already exists" in str(e).lower():
                return
            raise

    # ---------- 写入 ----------
    def add_texts(
        self,
        texts: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 128,
    ) -> List[str]:
        if not texts:
            return []
        if metadatas is None:
            metadatas = [{} for _ in texts]
        if not (len(texts) == len(vectors) == len(metadatas)):
            raise ValueError("texts / vectors / metadatas 长度必须一致")

        if self.embedding_dim is not None:
            for i, v in enumerate(vectors):
                if not isinstance(v, list) or len(v) != self.embedding_dim:
                    raise ValueError(
                        f"第 {i} 条向量维度={len(v)} 与 EMBEDDING_DIM={self.embedding_dim} 不一致"
                    )

        col = self.client.collections.get(self.collection)
        ids: List[str] = []
        with col.batch.dynamic() as b:
            b.batch_size = batch_size
            for t, v, m in zip(texts, vectors, metadatas):
                r = b.add_object(
                    properties={"text": t, "meta": json.dumps(m, ensure_ascii=False)},
                    vector=v,
                )
                ids.append(str(r))  # r 是 uuid.UUID
        return ids

    # ---------- 检索 ----------
    def search(self, query_vector: List[float], top_k: int = 8) -> List[Dict[str, Any]]:
        if not isinstance(query_vector, list) or not query_vector:
            raise ValueError("query_vector 不能为空")
        if self.embedding_dim is not None and len(query_vector) != self.embedding_dim:
            raise ValueError(
                f"查询向量维度={len(query_vector)} 与 EMBEDDING_DIM={self.embedding_dim} 不一致"
            )

        col = self.client.collections.get(self.collection)
        res = col.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=wq.MetadataQuery(distance=True),
        )

        hits: List[Dict[str, Any]] = []
        for o in (res.objects or []):
            try:
                meta = json.loads(o.properties.get("meta") or "{}")
            except Exception:
                meta = {"_raw_meta": o.properties.get("meta")}
            hits.append({
                "id": str(o.uuid),
                "distance": o.metadata.distance,  # 越小越相似
                "text": o.properties.get("text", ""),
                "metadata": meta,
            })
        return hits

    # ---------- 可选：清理 ----------
    def delete_collection(self) -> None:
        self.client.collections.delete(self.collection)

    # ---------- 资源释放 ----------
    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()
