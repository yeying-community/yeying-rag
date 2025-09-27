# rag/core/pipeline.py
# -*- coding: utf-8 -*-
"""
RAGPipeline: 结合主记忆 + 辅助记忆 + 知识库（预留）
- run(): 给定 query，拼接上下文，调用 LLM，返回答案
"""

from typing import Dict, Any, List
from rag.datasource.base import Datasource
from rag.memory.memory_manager import MemoryManager
from rag.llm.providers.openai_client import OpenAIClient


class RAGPipeline:
    def __init__(self, ds: Datasource, memory: MemoryManager, llm: OpenAIClient):
        """
        :param ds: Datasource 实例（封装 minio / weaviate / registry / primary / contexts）
        :param memory: MemoryManager 实例
        :param llm: LLM 客户端（默认用 OpenAIClient，可换）
        """
        self.ds = ds
        self.memory = memory
        self.llm = llm

    def _fetch_texts(self, urls: List[str]) -> List[str]:
        """
        从 MinIO 拉取一批 url 对应的正文
        """
        texts = []
        for url in urls:
            try:
                texts.append(self.ds.minio.get_text(url))
            except Exception as e:
                texts.append(f"[读取失败: {url}, 错误: {e}]")
        return texts

    def run(
        self,
        memory_id: str,
        app: str,
        query: str,
        summary_k: int = 1,
        recent_k: int = 6,
        aux_top_k: int = 5,
        aux_threshold: float = None,
        max_chars: int = 4000,
    ) -> Dict[str, Any]:
        """
        执行一次完整的 RAG 推理：
        1) 调用 MemoryManager 获取上下文（主记忆 + 辅助记忆）
        2) 从 MinIO 拉取正文
        3) 拼接上下文（有 token/字符限制）
        4) 调用 LLM 生成回答

        :return: { "answer": str, "context_used": dict }
        """
        # 1) 从记忆模块获取上下文
        ctx = self.memory.get_context(
            memory_id=memory_id,
            app=app,
            query=query,
            summary_k=summary_k,
            recent_k=recent_k,
            aux_top_k=aux_top_k,
            aux_threshold=aux_threshold,
        )
        # print(ctx)

        # 2) 拉取摘要和最近消息的正文
        texts = []
        texts.extend(self._fetch_texts(ctx.get("summary_urls", [])))
        texts.extend(self._fetch_texts(ctx.get("recent_urls", [])))

        # 3) 加上辅助记忆检索到的内容
        for hit in ctx.get("retrieved", []):
            texts.append(hit["content"])

        # print(" texts", texts)
        # 4) 拼接上下文（加长度限制）
        context = ""
        for t in texts:
            if len(context) + len(t) > max_chars:
                break
            context += "\n\n" + t

        # 5) 构造 prompt 并调用 LLM
        prompt = (
            f"以下是与用户相关的历史对话与信息，请结合它们回答用户问题。\n"
            f"--- 上下文开始 ---\n{context}\n--- 上下文结束 ---\n\n"
            f"用户问题：{query}\n请用简洁、准确的方式回答。"
        )

        answer = self.llm.complete(
            prompt,
            temperature=0.3,
            top_p=1.0,
            max_tokens=800,
            system="你是一个严谨的助手，会结合历史上下文回答用户问题。"
        )

        return {
            "answer": answer,
            "context_used": ctx
        }
