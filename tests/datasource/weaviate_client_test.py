# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
import uuid
import pytest

from rag.datasource.vectorstores.weaviate_store import WeaviateStore


@pytest.fixture(scope="module")
def store():
    # 随机集合名，避免脏数据影响
    col = f"pytest_ws_{uuid.uuid4().hex[:8]}"
    s = WeaviateStore(collection=col, embedding_dim=3)  # 测试用 3 维向量
    try:
        yield s
    finally:
        # 清理集合 & 关闭连接
        try:
            s.delete_collection()
        except Exception:
            pass
        try:
            s.close()
        except Exception:
            pass


def test_add_and_search_roundtrip(store: WeaviateStore):
    texts = [
        "AES-256 uses a 256-bit key and is considered secure.",
        "RC4 is a stream cipher with known vulnerabilities.",
        "RSA relies on integer factorization hardness.",
    ]
    # 与 embedding_dim=3 对齐的小向量（BYOV）
    vecs = [
        [0.10, 0.20, 0.30],
        [0.90, 0.10, 0.20],
        [-0.20, 0.00, 0.50],
    ]
    metas = [{"i": i, "source": "pytest"} for i in range(len(texts))]

    ids = store.add_texts(texts, vecs, metas)
    assert len(ids) == 3
    # id 是否是 UUID 格式
    _ = uuid.UUID(ids[0])

    # 用第一条向量做近邻检索，预期命中第一条文本在最前
    hits = store.search(vecs[0], top_k=2)
    assert len(hits) >= 1
    assert hits[0]["text"] == texts[0]
    assert "distance" in hits[0] and isinstance(hits[0]["distance"], float)


def test_empty_inputs_return_empty(store: WeaviateStore):
    # texts 为空时，应直接返回空列表
    assert store.add_texts([], [], []) == []


def test_length_mismatch_raises(store: WeaviateStore):
    # texts / vectors / metadatas 长度不一致应报错
    with pytest.raises(ValueError):
        store.add_texts(["only one"], [[0.1, 0.2, 0.3]], [])  # metadatas 缺失


def test_dim_mismatch_raises_on_add(store: WeaviateStore):
    # 写入维度与 embedding_dim(=3) 不一致时应报错
    with pytest.raises(ValueError):
        store.add_texts(["bad dim"], [[0.1, 0.2]], [{}])  # 2 维 vs 3 维


def test_dim_mismatch_raises_on_search(store: WeaviateStore):
    # 检索维度不一致也应报错
    with pytest.raises(ValueError):
        store.search([0.1, 0.2], top_k=1)  # 2 维 vs 3 维
