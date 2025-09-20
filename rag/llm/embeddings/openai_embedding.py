# rag/llm/embeddings/openai_embedding.py
import os
import time
from typing import List, Iterable

import httpx

DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_BASE = os.getenv("EMBED_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("EMBED_API_KEY", "")

class OpenAIEmbedder:
    def __init__(self, model: str = DEFAULT_EMBED_MODEL, timeout: float = 30.0):
        if not OPENAI_API_KEY:
            raise RuntimeError("API_KEY 未设置")
        self.model = model
        self.timeout = timeout

    def embed_query(self, text: str) -> List[float]:
        return self._embed_batch([text])[0]

    def embed_documents(self, texts: Iterable[str]) -> List[List[float]]:
        return self._embed_batch(list(texts))

    # --- 内部 ---
    def _embed_batch(self, inputs: List[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": inputs}
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        with httpx.Client(base_url=OPENAI_API_BASE, timeout=self.timeout) as client:
            # /embeddings
            for _ in range(3):
                try:
                    r = client.post("/embeddings", json=payload, headers=headers)
                    r.raise_for_status()
                    data = r.json()
                    return [item["embedding"] for item in data["data"]]
                except Exception as e:
                    time.sleep(1.2)
                    last_err = e
            raise RuntimeError(f"Embedding 失败: {last_err}")
