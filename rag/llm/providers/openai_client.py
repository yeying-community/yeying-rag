# -*- coding: utf-8 -*-
"""
极简 OpenAI 风格 LLM 封装（/v1/chat/completions）
- 适配标准 OpenAI 与兼容网关（如火山方舟 Ark 的 OpenAI 兼容端）
- 仅实现同步非流式调用（简单、稳定、好调试）
"""

import os
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    return v if v is not None and v != "" else default


DEFAULT_BASE = _env("OPENAI_API_BASE", "https://api.openai.com/v1")
DEFAULT_KEY = _env("OPENAI_API_KEY", "")
DEFAULT_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")


class OpenAIClient:
    def __init__(
        self,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ):
        """
        参数都可不传，默认从环境变量读取：
        - OPENAI_API_BASE, OPENAI_API_KEY, OPENAI_MODEL
        """
        self.model = model or DEFAULT_MODEL
        self.api_base = (api_base or DEFAULT_BASE).rstrip("/")
        self.api_key = api_key or DEFAULT_KEY
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY 未设置")
        self.timeout = timeout
        self.max_retries = max_retries

    # --------------- Public APIs ---------------

    def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
        top_p: float = 1.0,
        max_tokens: int = 1024,
        system: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """给纯字符串的便捷接口"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        text, _raw = self.chat(
            messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            extra=extra,
        )
        return text

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.2,
        top_p: float = 1.0,
        max_tokens: int = 1024,
        response_format: Optional[Dict[str, Any]] = None,  # 例如 {"type":"json_object"}
        extra: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        标准 /v1/chat/completions 调用
        返回：(text, raw_json)
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        if extra:
            payload.update(extra)

        headers = {"Authorization": f"Bearer {self.api_key}"}

        # 简单重试（指数退避）
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                with httpx.Client(base_url=self.api_base, timeout=self.timeout) as client:
                    r = client.post("/chat/completions", headers=headers, json=payload)
                    r.raise_for_status()
                    data = r.json()
                text = (
                    data["choices"][0]["message"]["content"]
                    if data.get("choices")
                    else ""
                )
                return text, data
            except Exception as e:
                last_err = e
                # 429/5xx 等退避；第 n 次退 n*0.8s
                time.sleep(0.8 * (attempt + 1))
        raise RuntimeError(f"OpenAI chat 调用失败: {last_err}")

    def rag_answer(
        self,
        question: str,
        contexts: Iterable[str],
        *,
        system: str = (
            "你是一个严谨的助手。仅基于提供的上下文回答；"
            "若缺少信息，请明确说明“根据已知上下文无法回答”。"
        ),
        temperature: float = 0.2,
        top_p: float = 1.0,
        max_tokens: int = 768,
        extra: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        RAG 常用封装：把若干 context 拼接后与问题一起发送
        """
        ctx_text = "\n\n---\n\n".join([c.strip() for c in contexts if c and c.strip()])
        user = (
            "【问题】\n"
            f"{question.strip()}\n\n"
            "【检索到的上下文】\n"
            f"{ctx_text}\n\n"
            "【要求】\n"
            "1) 仅依据“上下文”作答；2) 若上下文不足，请回答“根据已知上下文无法回答”。"
        )
        return self.complete(
            user,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            system=system,
            extra=extra,
        )
