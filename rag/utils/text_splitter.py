# rag/utils/text_splitter.py
# -*- coding: utf-8 -*-
"""
极简文本切分：
- 依据字符长度的滑动窗口
- 优先在自然断点（\n\n, \n, 空白、常见中英文标点）截断
- 支持 overlap
- 返回每段的原文偏移（start, end），便于引用/定位

只依赖标准库，适合 .md / .txt。
"""

from __future__ import annotations
from typing import List, Dict

# 自然断点优先级（从高到低）
BREAK_CANDIDATES = [
    "\n\n",          # 段落
    "\n",            # 换行
    "。", "！", "？",  # 中文句末
    ". ", "! ", "? ",  # 英文句末（带空格以免截掉句点后接单词）
    "；", "，", ", ",  # 次级标点
    " ",             # 空白
]

def _normalize(text: str) -> str:
    # 统一换行 & 去 BOM
    t = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    return t

def _find_break(text: str, start: int, hard_limit: int) -> int:
    """
    在 [start, hard_limit] 范围内，尽量向左找到一个自然断点。
    找不到就返回 hard_limit（硬切）。
    """
    if hard_limit >= len(text):
        hard_limit = len(text)

    window = text[start:hard_limit]
    # 从优先级高到低寻找“最后一次出现”的断点
    best = -1
    best_len = 0
    for sep in BREAK_CANDIDATES:
        idx = window.rfind(sep)
        if idx >= 0:
            # 把相对位置转成全局位置
            pos = start + idx + len(sep)
            if pos > best:
                best = pos
                best_len = len(sep)
    return best if best >= 0 else hard_limit

def simple_split(text: str, chunk_size: int = 1024, overlap: int = 150) -> List[Dict]:
    """
    将文本切分为若干块：
    - chunk_size: 目标上限（字符数）
    - overlap: 相邻块重叠字符数（用于保持上下文连续）
    返回: [{ "text": str, "start": int, "end": int }, ...]
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须 > 0")
    if overlap < 0:
        raise ValueError("overlap 不能为负")
    if overlap >= chunk_size:
        # 防止死循环：重叠不能大于等于块大小
        overlap = max(0, chunk_size // 4)

    src = _normalize(text)
    n = len(src)
    if n == 0:
        return []

    chunks: List[Dict] = []
    start = 0
    while start < n:
        hard_limit = min(n, start + chunk_size)
        end = _find_break(src, start, hard_limit)
        if end <= start:
            # 极限兜底，避免死循环
            end = min(n, start + chunk_size)

        seg = src[start:end].strip()
        # 记录的是规范化文本的偏移；如需映射到原始文本，可在上层自行维护
        if seg:
            chunks.append({"text": seg, "start": start, "end": end})

        if end >= n:
            break
        # 下一个窗口起点 = 本段结束 - overlap
        start = max(0, end - overlap)
        # 若没有推进（例如 overlap 太大且 seg 被 strip 成空），强制 +1
        if chunks and start <= chunks[-1]["end"] - len(chunks[-1]["text"]):
            start = end

    return chunks
