# rag/core/pipeline.py
# -*- coding: utf-8 -*-
"""
RAGPipeline: 结合主记忆 + 辅助记忆 + 知识库（预留）
- run(): 给定 query，拼接上下文，调用 LLM，返回答案
"""
import json
import re
from typing import Dict, Any, List
from rag.datasource.base import Datasource
from rag.memory.memory_manager import MemoryManager
from rag.llm.providers.openai_client import OpenAIClient
from rag.core.retriever_jd import JDRetriever

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
        这个函数是只结合记忆能力回答用户的问题
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

    def generate_interview_questions(
            self,
            memory_id: str,
            app: str,
            query: str,
            company: str | None = None,
            target_position: str | None = None,
            jd_top_k: int = 3,
            memory_top_k: int = 3,
            max_chars: int = 500,
    ):
        """
        面试官场景：结合候选人信息 + JD 库内容生成面试题目（不含答案）
        """
        # 1️⃣ 获取记忆上下文
        ctx = self.memory.get_context(
            memory_id=memory_id,
            app=app,
            query=query,
            recent_k=memory_top_k,
            summary_k=1
        )

        texts = []
        texts.extend(self._fetch_texts(ctx.get("summary_urls", [])))
        texts.extend(self._fetch_texts(ctx.get("recent_urls", [])))

        for hit in ctx.get("retrieved", []):
            texts.append(hit["content"])

        context = "\n\n".join(texts)[:max_chars]

        # 2️⃣ JD 库检索（可按公司/岗位过滤）
        retriever = JDRetriever(collection="InterviewerJDKnowledge", company=company)
        jd_hits = retriever.search(target_position or query, top_k=jd_top_k)
        jd_context = "\n".join([
            f"公司：{h['company']} 职位：{h['position']}\n要求：{h['requirements']}\n描述：{h['description']}"
            for h in jd_hits
        ])[:max_chars]

        # 3️⃣ 拼提示词
        prompt = f"""
        你是资深面试官助手，请结合候选人信息与岗位要求，为面试官生成面试题目。
        注意：
        - 只输出问题，不要写答案；
        - 每个问题应体现岗位核心能力；
        - 若有目标岗位，请优先参考 JD 的要求；
        - 若信息不足，请给出通用技术问题；
        - 最终输出格式必须严格为 JSON 对象，字段名为 "questions"，其值为字符串数组。

        输出示例：
        {{
          "questions": [
            "请你介绍一次在推荐系统中使用强化学习的经历。",
            "在模型训练中，你如何平衡精度和性能？",
            "请谈谈样本不平衡问题的应对策略。"
          ]
        }}

        【候选人与上下文】
        {context}

        【岗位信息（JD）】
        {jd_context}

        【面试官请求】
        {query}

        请生成3~5个面试题，并严格输出为 JSON 格式：
        """

        # 4️⃣ 调 LLM
        result = self.llm.complete(
            prompt,
            temperature=0.5,
            max_tokens=800,
            system="你是面试官助手，只输出题目，不解释或回答。"
        )

        return {
        "questions": self._extract_questions(result),
        "context_used": {
            "memory_context": ctx,
            "jd_context_preview": jd_context[:500]
    }}

    def _extract_questions(self, text: str) -> list[str]:
        """解析 LLM 输出为题目列表（支持 JSON + 文本两种格式）"""
        text = text.strip()

        # ✅ 优先尝试 JSON 解析
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "questions" in data:
                q_list = data["questions"]
                if isinstance(q_list, list):
                    return [q.strip() for q in q_list if isinstance(q, str) and len(q.strip()) > 2]
        except Exception:
            pass

        # ⚙️ 回退方案：逐行提取（适配 markdown / 编号格式）
        lines = re.findall(r"[-•]?\s*\d*[\.\)]?\s*(.+)", text)
        clean = [l.strip() for l in lines if 4 < len(l.strip()) < 200]
        return clean[:10]  # 限制最多10个题目