# -*- coding: utf-8 -*-
"""
WeaviateStore (v4 专用)
- BYOV（自带向量）
- 支持 add_texts / batch_upsert / search / query_by_text / replace_one / delete / list_collections
- 封装 app/memory_id 元数据，方便做过滤
"""

import os
import json
import time
from typing import List, Dict, Any, Optional

import weaviate
import weaviate.classes.config as wc
import weaviate.classes.query as wq
from weaviate.exceptions import UnexpectedStatusCodeError
from weaviate.classes.query import Filter
from rag.datasource.connections.weaviate_connection import WeaviateConnection


def _norm_class(name: str) -> str:
    """规范化 Collection 名称（首字母必须大写，且只允许字母数字）"""
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
    def __init__(
        self,
        collection: Optional[str] = None,
        conn: Optional[WeaviateConnection] = None,
        embedding_dim: Optional[int] = None,
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

    # ---------- Schema ----------
    def _ensure_collection(self) -> None:
        try:
            col = self.client.collections.get(self.collection)
            for name in ["text", "meta", "memory_id", "app"]:
                try:
                    col.config.add_property(wc.Property(name=name, data_type=wc.DataType.TEXT))
                except Exception:
                    pass
            return
        except Exception:
            pass

        try:
            self.client.collections.create(
                name=self.collection,
                properties=[
                    wc.Property(name="text", data_type=wc.DataType.TEXT),
                    wc.Property(name="meta", data_type=wc.DataType.TEXT),
                    wc.Property(name="memory_id", data_type=wc.DataType.TEXT),
                    wc.Property(name="app", data_type=wc.DataType.TEXT),
                ],
                vector_config=wc.Configure.Vectors.self_provided(),
            )
        except UnexpectedStatusCodeError as e:
            if "already exists" in str(e).lower():
                return
            raise

    def ensure_collection(self, name: str, properties: Optional[list] = None) -> None:
        """
        主要目标是单独保证特定的collection的存在，在Datasource初始化时调用，原有_ensure_collection 管理默认的 KbDefault collection
        确保指定的 collection 存在，如果不存在则创建
        - name: collection 名称
        - properties: 需要的字段定义
        """
        col_name = _norm_class(name)
        try:
            col = self.client.collections.get(col_name)
            # 尝试补充缺失的属性
            if properties:
                for p in properties:
                    try:
                        col.config.add_property(p)
                    except Exception:
                        pass
            return
        except Exception:
            pass

        # 不存在则新建
        props = properties or [
            wc.Property(name="text", data_type=wc.DataType.TEXT),
            wc.Property(name="meta", data_type=wc.DataType.TEXT),
            wc.Property(name="memory_id", data_type=wc.DataType.TEXT),
            wc.Property(name="app", data_type=wc.DataType.TEXT),
        ]

        self.client.collections.create(
            name=col_name,
            properties=props,
            vector_config=wc.Configure.Vectors.self_provided(),
        )

    # ---------- 写入 ----------
    def add_texts(
        self,
        texts: List[str],
        vectors: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        memory_id: Optional[str] = None,
        app: Optional[str] = None,
        collection: Optional[str] = None,  #新增，之前没有指定集合
    ) -> List[str]:
        if not texts:
            return []
        if metadatas is None:
            metadatas = [{} for _ in texts]
        if not (len(texts) == len(vectors) == len(metadatas)):
            raise ValueError("texts / vectors / metadatas 长度必须一致")

        if self.embedding_dim is not None:
            for i, v in enumerate(vectors):
                if len(v) != self.embedding_dim:
                    raise ValueError(f"第 {i} 条向量维度={len(v)} 与 EMBEDDING_DIM={self.embedding_dim} 不一致")

        # ✅ 改为按参数决定 collection（缺省仍用 self.collection）
        col_name = _norm_class(collection or self.collection)
        col = self.client.collections.get(col_name)

        ids: List[str] = []
        with col.batch.dynamic() as batch:
            for t, v, m in zip(texts, vectors, metadatas):
                #  属性里同时写入 url/role，方便过滤删除与直接读取
                props = {
                    "text": t,
                    "meta": json.dumps(m or {}, ensure_ascii=False),
                    "url": (m or {}).get("url"),  # ✅ 新增
                    "role": (m or {}).get("role"),  # ✅ 新增
                }
                if memory_id:
                    props["memory_id"] = str(memory_id)
                if app:
                    props["app"] = str(app)

                r = batch.add_object(properties=props, vector=v)
                ids.append(str(r))
        return ids

    def batch_upsert(
        self,
        texts: List[str],
        vectors: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        memory_id: Optional[str] = None,
        app: Optional[str] = None,
    ) -> List[str]:
        if vectors is not None and len(vectors) != len(texts):
            raise ValueError("vectors 长度必须与 texts 相同")
        if ids is not None and len(ids) != len(texts):
            raise ValueError("ids 长度必须与 texts 相同")
        if metadatas is not None and len(metadatas) != len(texts):
            raise ValueError("metadatas 长度必须与 texts 相同")

        col = self.client.collections.get(self.collection)
        uuids: List[str] = []
        with col.batch.dynamic() as batch:
            for i, text in enumerate(texts):
                props = {"text": text, "meta": json.dumps(metadatas[i] if metadatas else {})}
                if memory_id:
                    props["memory_id"] = str(memory_id)
                if app:
                    props["app"] = str(app)

                vec = vectors[i] if vectors else None
                uid = ids[i] if ids else None

                if uid:
                    col.data.replace(uuid=uid, properties=props, vector=vec)
                    uuids.append(uid)
                else:
                    r = batch.add_object(properties=props, vector=vec)
                    uuids.append(str(r))
        return uuids

    # ---------- 检索 ----------
    def search(self, query_vector: List[float], top_k: int = 8,
               collection: Optional[str] = None,
               filters: Optional[dict] = None,  # 例如 {"memory_id": "...", "app": "..."}
               return_meta: bool = True,) -> List[Dict[str, Any]]:
        if self.embedding_dim and len(query_vector) != self.embedding_dim:
            raise ValueError(f"查询向量维度={len(query_vector)} 与 EMBEDDING_DIM={self.embedding_dim} 不一致")

        # 增加传参指定查询collection
        col_name = _norm_class(collection or self.collection)
        col = self.client.collections.get(col_name)

        # 把原来的过滤条件，集成到Filter中
        where = None
        if filters:
            clauses = []
            for k, v in filters.items():
                clauses.append(Filter.by_property(k).equal(v))
            where = Filter.all_of(clauses)

        res = col.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=wq.MetadataQuery(distance=True),
            filters=where,
        )
        hits = []
        for o in res.objects or []:
            props = o.properties or {}
            # 统一转成 score (certainty 如果有, 否则 distance->score)
            dist = getattr(o.metadata, "distance", None)
            # 统一到 score：越大越相关
            score = 1 / (1 + dist) if dist is not None else 0.0
            hits.append({"properties": props, "score": score})
        return hits

    def query_by_text(
        self, query: str, top_k: int = 8,
        memory_id: Optional[str] = None, app: Optional[str] = None,
        hybrid: bool = False, query_vector: Optional[List[float]] = None, alpha: float = 0.5
    ) -> List[Dict[str, Any]]:
        col = self.client.collections.get(self.collection)
        flt = None
        if memory_id:
            flt = wq.Filter.by_property("memory_id").equal(str(memory_id))
            if app:
                flt = flt & wq.Filter.by_property("app").equal(str(app))
        elif app:
            flt = wq.Filter.by_property("app").equal(str(app))

        if hybrid:
            res = col.query.hybrid(
                query=query,
                vector=query_vector,
                alpha=alpha,
                limit=top_k,
                filters=flt,
                return_metadata=wq.MetadataQuery(score=True, distance=True),
            )
        else:
            res = col.query.bm25(
                query=query,
                limit=top_k,
                filters=flt,
                return_metadata=wq.MetadataQuery(score=True),
            )

        return [
            {
                "id": str(o.uuid),
                "score": getattr(o.metadata, "score", None),
                "distance": getattr(o.metadata, "distance", None),
                "text": o.properties.get("text", ""),
                "metadata": json.loads(o.properties.get("meta") or "{}"),
                "memory_id": o.properties.get("memory_id"),
                "app": o.properties.get("app"),
            }
            for o in (res.objects or [])
        ]

    # ---------- 删除 ----------
    def delete(self, object_id: str) -> bool:
        """v4 delete 幂等，总是返回 True"""
        col = self.client.collections.get(self.collection)
        try:
            col.data.delete_by_id(object_id)
            return True
        except Exception:
            return False

    def delete_by_ids(self, ids: List[str]) -> int:
        col = self.client.collections.get(self.collection)
        ok = 0
        for _id in ids:
            try:
                col.data.delete_by_id(_id)
                ok += 1
            except Exception:
                pass
        return ok

    # --- Delete by filter ---
    def delete_by_filter(self, collection: str, filters: dict) -> int:
        """
        按过滤条件批量删除
        """
        col_name = _norm_class(collection or self.collection)
        col = self.client.collections.get(col_name)

        clauses = []
        for k, v in filters.items():
            clauses.append(Filter.by_property(k).equal(v))
        where = Filter.all_of(clauses) if clauses else None

        result = col.data.delete_many(where=where)
        return result.get("results", {}).get("matches", 0)

    # ---------- 替换 ----------
    def replace_one(self, _id: str, text: str, vector: List[float],
                    metadata: Optional[Dict[str, Any]] = None,
                    memory_id: Optional[str] = None,
                    app: Optional[str] = None) -> bool:
        col = self.client.collections.get(self.collection)
        props = {"text": text, "meta": json.dumps(metadata or {}, ensure_ascii=False)}
        if memory_id:
            props["memory_id"] = str(memory_id)
        if app:
            props["app"] = str(app)
        try:
            col.data.replace(uuid=_id, properties=props, vector=vector)
            time.sleep(0.5)  # 等待索引刷新更久一点
            return True
        except Exception:
            return False

    # ---------- Collection 管理 ----------
    def list_collections(self) -> List[str]:
        cols = self.client.collections.list_all()
        return [c if isinstance(c, str) else getattr(c, "name", str(c)) for c in cols]

    def delete_collection(self) -> None:
        self.client.collections.delete(self.collection)

    # ---------- 清理 ----------
    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __del__(self):
        self.close()
