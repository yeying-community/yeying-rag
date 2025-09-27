# rag/memory/primary_memory.py
# -*- coding: utf-8 -*-
"""
PrimaryMemory: 主记忆高层接口
- create_memory(): 初始化记忆空间
- push(): 登记一条新的上下文消息
"""

import hashlib
import time
import uuid
from typing import Optional, Dict, Any

from rag.datasource.base import Datasource
from rag.llm.providers.openai_client import OpenAIClient


class PrimaryMemory:
    def __init__(self, ds: Datasource):
        """
        :param ds: Datasource 实例，聚合了 mem_registry/mem_primary/mem_contexts/minio 等
        """
        self.ds = ds

    # ---------- 第 1 步：初始化 ----------
    def create_memory(self, app: str, params: Optional[Dict[str, Any]] = None) -> str:
        """

        初始化记忆空间：
        - 在 registry 中注册
        - 在 primary 表中新建/更新进度行
        """
        memory_id = f"{app}_{uuid.uuid4().hex[:12]}"  # app前缀 + 随机串

        self.ds.mem_registry.upsert(memory_id=memory_id, app=app, params=params)
        self.ds.mem_primary.upsert(memory_id)

        return memory_id

    # ---------- 第 2 步：push ----------
    def push(
        self,
        memory_id: str,
        app: str,
        url: str,
        description: Optional[str] = None,
        ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        登记一条新的上下文消息（正文已由业务层写入 MinIO，只传 URL）
        - uid: uuid唯一记录上下文
        - content_sha256: 基于 url 的 hash，用于幂等
        - 记录写入 mem_contexts
        - 计数器 bump_total
        """
        ts = ts or time.time()
        uid = str(uuid.uuid4())[:16]
        content_sha256 = hashlib.sha256(url.encode("utf-8")).hexdigest()

        row = self.ds.mem_contexts.create(
            uid=uid,
            memory_id=memory_id,
            app=app,
            url=url,
            content_sha256=content_sha256,
            description=description,
        )

        # 更新计数器
        self.ds.mem_primary.bump_total(memory_id, delta=1)

        return row

    # ---------- 第 3 步：summarize ----------
    def maybe_summarize(self, memory_id: str, app: str) -> Optional[str]:
        """
        当 recent_qa_count ≥ summary_every_n 时触发摘要。
        新的摘要会覆盖之前的摘要 + 新增的消息，保证主记忆中始终只有一份最新摘要。
        """

        # 1) 读取 registry 配置
        reg_row = self.ds.mem_registry.get(memory_id)
        if not reg_row:
            raise ValueError(f"Memory {memory_id} not found in registry")

        import json
        params = {}
        if reg_row.get("params_json"):
            try:
                params = json.loads(reg_row["params_json"])
            except Exception:
                params = {}

        threshold = params.get("summary_every_n", 5)
        max_tokens = params.get("max_summary_tokens", 512)
        summary_lang = params.get("summary_language", "zh")

        # 2) 读取 primary 进度
        pri_row = self.ds.mem_primary.get(memory_id)
        if not pri_row:
            raise ValueError(f"Memory {memory_id} not found in primary")

        recent_count = pri_row.get("recent_qa_count", 0)
        if recent_count < threshold:
            return None

        # 3) 收集已有摘要 + 未摘要消息
        texts = []

        # 如果已有摘要，先加入旧摘要内容
        if pri_row.get("summary_url"):
            try:
                old_summary = self.ds.minio.get_text(pri_row["summary_url"])
                texts.append(old_summary)
            except Exception:
                texts.append("[读取旧摘要失败]")

        # 找出新消息
        contexts = self.ds.mem_contexts.list_by_memory(memory_id, limit=threshold * 2)
        contexts = [c for c in contexts if not self.ds.mem_deleted.is_deleted(c["url"])]
        window = [c for c in contexts if not c.get("is_summarized")]

        if not window and not texts:
            return None

        for ctx in window:
            url = ctx["url"]
            try:
                texts.append(self.ds.minio.get_text(url))
            except Exception:
                texts.append(f"[读取失败: {url}]")

        # 4) 调用 OpenAI summarizer
        client = OpenAIClient()
        system_prompt = "你是一个严谨的摘要助手。"
        if summary_lang == "en":
            system_prompt = "You are a precise summarization assistant."

        prompt = (
                "请对以下多轮对话做简洁的总结，保留重要事实、实体和关键决策，"
                "忽略闲聊与重复内容。输出一段摘要。\n\n"
                + "\n\n---\n\n".join(texts)
        )

        summary_text = client.complete(
            prompt,
            temperature=0.2,
            top_p=1.0,
            max_tokens=max_tokens,
            system=system_prompt,
        )

        # 5) 写入新的摘要文件
        key = self.ds.minio.make_key(app, memory_id, ext="md")
        self.ds.minio.put_text(key, summary_text)
        summary_url = key

        # 6) 更新 PrimaryStore
        self.ds.mem_primary.update_summary(memory_id, summary_url)
        new_index = pri_row.get("total_qa_count", 0)
        self.ds.mem_primary.advance_index(memory_id, new_index)

        # 7) 标记窗口内的消息为已摘要
        for ctx in window:
            self.ds.mem_contexts.mark_summarized(ctx["uid"])

        return summary_url

    # ---------- 第 4 步：get_context ----------
    def get_context(
        self,
        memory_id: str,
        summary_k: int = 1,
        recent_k: int = 6,
    ) -> Dict[str, list]:
        """
        目前只支持取 1 条最新摘要，未来扩展多摘要时才用 summary_k

        返回指定 memory 的上下文：
        - 最近 summary_k 条摘要 URL（M1 简化为只取 1 条）
        - 最近 recent_k 条未摘要消息 URL
        """
        result = {"summary_urls": [], "recent_urls": []}

        # 1) 取摘要 URL
        pri_row = self.ds.mem_primary.get(memory_id)

        print("取摘要 URL", pri_row)
        if pri_row and pri_row.get("summary_url"):
            result["summary_urls"] = [pri_row["summary_url"]]

        # 2) 取最近未摘要的消息
        contexts = self.ds.mem_contexts.list_by_memory(memory_id, limit=recent_k * 2)
        print("<UNK> contexts", contexts)
        unsummarized = [c for c in contexts if not c.get("is_summarized")]
        recent_urls = [c["url"] for c in unsummarized[:recent_k]]

        result["recent_urls"] = recent_urls
        return result

    # ---------- M2: 删除接口 ----------
    def delete_message(self, memory_id: str, url: str) -> None:
        """
        逻辑删除一条消息，不物理删除。
        """
        self.ds.mem_deleted.mark_deleted(memory_id, url)

    # ---------- M2: 并发安全（轻量 CAS 示例） ----------
    def safe_push(self, *args, retries: int = 3, **kwargs) -> Dict[str, Any]:
        """
        带重试的 push，避免并发冲突。
        """
        for i in range(retries):
            try:
                return self.push(*args, **kwargs)
            except Exception as e:
                if i == retries - 1:
                    raise
                time.sleep(0.1 * (i + 1))  # 退避重试
