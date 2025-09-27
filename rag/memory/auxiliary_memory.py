# rag/memory/auxiliary_memory.py
# -*- coding: utf-8 -*-
"""
AuxiliaryMemory: 辅助记忆模块
- A1: add_message() 从 MinIO 读取 QA，逐条向量化并存入 Weaviate
- A2: search() 输入 query，向量化后检索相似历史消息
- A3: delete_message() 删除某个 url 对应的所有 QA
- A3: clear_memory() 清空整个 memory_id 的辅助记忆
- A4: 配置化，从 mem_registry.params_json 读取默认参数
"""

import json
from typing import Optional, Dict, Any, List
from rag.datasource.base import Datasource
from rag.llm.embeddings.openai_embedding import OpenAIEmbedder


class AuxiliaryMemory:
    def __init__(self, ds: Datasource, embedder: Optional[OpenAIEmbedder] = None):
        """
        :param ds: Datasource 实例（聚合 weaviate, minio, registry）
        :param embedder: embedding 模型实例（默认 OpenAIEmbedder）
        """
        self.ds = ds
        self.embedder = embedder or OpenAIEmbedder()

        if getattr(self.ds, "weaviate", None) is None:
            raise RuntimeError("Datasource.weaviate 未启用，请配置 WEAVIATE_ENABLED")

    # ---------- 内部工具 ----------
    def _get_params(self, memory_id: str) -> dict:
        """从 mem_registry 读取配置参数"""
        reg_row = self.ds.mem_registry.get(memory_id)
        if not reg_row:
            return {}

        params = {}
        if reg_row.get("params_json"):
            try:
                params = json.loads(reg_row["params_json"])
            except Exception:
                params = {}
        return params

    # ---------- A1: 基础存储 ----------
    def add_message(
        self,
        memory_id: str,
        app: str,
        url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        从 MinIO 读取 QA，逐条向量化并写入向量数据库
        :param memory_id: 记忆空间 ID
        :param app: 业务 app 名
        :param url: MinIO 对象 key（存放 QA JSON 或文本）
        :param metadata: 附加元信息
        :return: 对象 ID 列表
        """
        # 1) 从 MinIO 读取内容
        raw_text = self.ds.minio.get_text(url)

        # 2) 尝试解析 QA
        try:
            data = json.loads(raw_text)
            if isinstance(data, list):
                messages = data
            elif isinstance(data, dict) and "qa" in data:
                messages = data["qa"]
            else:
                messages = [{"role": "user", "content": raw_text}]
        except Exception:
            messages = [{"role": "user", "content": raw_text}]

        texts, vectors, metas = [], [], []
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "user")
            if not content.strip():
                continue

            # 3) 向量化
            vec = self.embedder.embed_query(content)

            # 4) 准备写入
            texts.append(content)
            vectors.append(vec)
            meta = {"url": url, "role": role}
            if metadata:
                meta.update(metadata)
            metas.append(meta)

        # 5) 写入 Weaviate
        ids = self.ds.weaviate.add_texts(
            texts=texts,
            vectors=vectors,
            metadatas=metas,
            memory_id=memory_id,
            app=app,
            collection="AuxiliaryMemory",
        )
        return ids

    # ---------- A2: 相似检索 ----------
    def search(
        self,
        memory_id: str,
        app: str,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ):
        """
        在指定 memory_id 下检索与 query 最相关的历史消息。
        支持从 params_json 读取默认配置。
        """
        # 1) 从 registry 读取配置
        params = self._get_params(memory_id)
        if top_k is None:
            top_k = params.get("aux_top_k", 5)
        if score_threshold is None:
            score_threshold = params.get("aux_score_threshold")

        embed_model = params.get("embedding_model")
        if embed_model and getattr(self.embedder, "model", None) != embed_model:
            # 动态切换 embedder 模型
            self.embedder.model = embed_model

        # 2) 向量化 query
        q_vec = self.embedder.embed_query(query)

        # 3) 调用 weaviate 搜索
        results = self.ds.weaviate.search(
            collection="AuxiliaryMemory",
            query_vector=q_vec,
            top_k=top_k,
            filters={"memory_id": memory_id, "app": app},
        )
        print("Weaviate results", results)

        # 4) 格式化输出
        hits = []
        for r in results:
            score = r.get("score", 0.0)

            if score_threshold is not None and score < score_threshold:
                continue
            props = r.get("properties", {}) or {}
            # text 直接在属性里
            content = props.get("text")
            # meta 需要反序列化，且我们也写了独立属性 url/role（优先取独立属性）
            meta = {}
            try:
                meta = json.loads(props.get("meta") or "{}")
            except Exception:
                meta = {}

            url = props.get("url") or meta.get("url")
            role = props.get("role") or meta.get("role")

            hits.append({
                "content": content,  # Weaviate 结果里的文本字段
                "url": url,
                "role": role,
                "score": score,
            })
        return hits

    # ---------- A3: 删除 ----------
    def delete_message(self, memory_id: str, app: str, url: str) -> int:
        """
        从向量库中删除属于指定 memory_id + url 的所有 QA。
        """
        deleted = self.ds.weaviate.delete_by_filter(
            collection="AuxiliaryMemory",
            filters={"memory_id": memory_id, "app": app, "url": url},
        )
        return deleted

    def clear_memory(self, memory_id: str, app: str) -> int:
        """
        清空某个 memory_id 下的所有辅助记忆。
        """
        deleted = self.ds.weaviate.delete_by_filter(
            collection="AuxiliaryMemory",
            filters={"memory_id": memory_id, "app": app},
        )
        return deleted
