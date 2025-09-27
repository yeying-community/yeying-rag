# rag/memory/memory_manager.py
# -*- coding: utf-8 -*-
"""
MemoryManager: 记忆协调层
- 封装 PrimaryMemory + AuxiliaryMemory
- 提供统一接口：create / push / delete / clear
"""

from typing import Optional, Dict, Any
from rag.datasource.base import Datasource
from rag.llm.embeddings.openai_embedding import OpenAIEmbedder
from rag.memory.primary_memory import PrimaryMemory
from rag.memory.auxiliary_memory import AuxiliaryMemory


class MemoryManager:
    def __init__(self, ds: Datasource, embedder: Optional[OpenAIEmbedder] = None):
        """
        :param ds: Datasource 实例
        """
        self.ds = ds
        self.primary = PrimaryMemory(ds)
        self.auxiliary = AuxiliaryMemory(ds, embedder=embedder)

    # ---------- 创建 ----------
    def create_memory(self, app: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        创建一个新的记忆空间，返回 memory_id
        """
        return self.primary.create_memory(app, params)

    # ---------- 写入 ----------
    def push_message(self, memory_id: str, app: str, url: str, description: Optional[str] = None):
        """
        写入一条新消息：
        - 主记忆登记元信息
        - 辅助记忆向量化并入库
        """
        try:
            # 主记忆写入
            row = self.primary.push(memory_id=memory_id, app=app, url=url, description=description)
            summarize_url = self.primary.maybe_summarize(memory_id=memory_id,app=app)
            # print(summarize_url)
            # 辅助记忆写入
            self.auxiliary.add_message(memory_id=memory_id, app=app, url=url)
            return row
        except Exception as e:
            # TODO: 可扩展回滚逻辑（例如删除主记忆记录）
            raise RuntimeError(f"push_message 失败: {e}")

    # ---------- 删除 ----------
    def delete_message(self, memory_id: str, app: str, url: str):
        """
        删除一条消息：
        - 主记忆逻辑删除
        - 辅助记忆物理删除
        """
        self.primary.delete_message(memory_id=memory_id, url=url)
        self.auxiliary.delete_message(memory_id=memory_id, app=app, url=url)

    # ---------- 清空 ----------
    def clear_memory(self, memory_id: str, app: str):
        """
        清空整个 memory_id 的所有消息：
        - 主记忆：TODO（未来可加 truncate 功能）
        - 辅助记忆：物理删除全部
        """
        self.auxiliary.clear_memory(memory_id=memory_id, app=app)
        # 主记忆暂时没有 clear_all，可按需实现

    def get_context(
        self,
        memory_id: str,
        app: str,
        query: str,
        summary_k: int = 1,
        recent_k: int = 6,
        aux_top_k: int = 5,
        aux_threshold: float = None,
    ) -> Dict[str, Any]:
        """
        融合主记忆和辅助记忆，返回上下文给 pipeline 使用。

        :param memory_id: 记忆空间 ID
        :param app: 业务 app 名
        :param query: 当前查询文本
        :param summary_k: 主记忆摘要数量（默认 1）
        :param recent_k: 主记忆最近消息数量
        :param aux_top_k: 辅助记忆召回条数
        :param aux_threshold: 辅助记忆得分阈值
        :return: {
            "summary_urls": [...],
            "recent_urls": [...],
            "retrieved": [
                {"content": ..., "url": ..., "role": ..., "score": ...}
            ]
        }
        """
        # 1) 主记忆：摘要 + 最近消息
        pri_ctx = self.primary.get_context(
            memory_id=memory_id,
            summary_k=summary_k,
            recent_k=recent_k,
        )

        # 2) 辅助记忆：语义检索
        aux_hits = self.auxiliary.search(
            memory_id=memory_id,
            app=app,
            query=query,
            top_k=aux_top_k,
            score_threshold=aux_threshold,
        )

        # 3) 融合
        return {
            "summary_urls": pri_ctx.get("summary_urls", []),
            "recent_urls": pri_ctx.get("recent_urls", []),
            "retrieved": aux_hits,
        }
