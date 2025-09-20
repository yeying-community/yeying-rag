# -*- coding: utf-8 -*-
import os
import pytest

from rag.datasource.vectorstores.weaviate_store import WeaviateStore
from rag.datasource.connections.weaviate_connection import WeaviateConnection

WEAVIATE_SCHEME = os.getenv("WEAVIATE_SCHEME", "http")
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "test-weaviate.yeying.pub")
WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT", "8080"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY") or None

TEST_COLLECTION = os.getenv("WEAVIATE_TEST_COLLECTION", "TestRAGChunks_pytest")
VEC_DIM = int(os.getenv("WEAVIATE_TEST_VEC_DIM", "16"))


def _vec(val: float, n: int = VEC_DIM):
    return [val] * n


@pytest.fixture(scope="session")
def store():
    conn = WeaviateConnection(
        scheme=WEAVIATE_SCHEME,
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT,
        grpc_port=WEAVIATE_GRPC_PORT,
        api_key=WEAVIATE_API_KEY,
    )
    if not conn.client.is_ready():
        pytest.skip("Weaviate 不可用，跳过测试")

    s = WeaviateStore(collection=TEST_COLLECTION, conn=conn, embedding_dim=VEC_DIM)
    yield s

    try:
        s.delete_collection()
    except Exception:
        pass


def test_add_and_search(store: WeaviateStore):
    texts = ["AES-GCM provides AEAD.", "Diffie-Hellman key exchange."]
    vecs = [_vec(0.1), _vec(0.2)]
    ids = store.add_texts(texts, vecs, memory_id="mem1", app="interviewer")
    assert len(ids) == 2

    hits = store.search(_vec(0.1), top_k=2, memory_id="mem1", app="interviewer")
    assert any("AES" in h["text"] for h in hits)


def test_query_by_text(store: WeaviateStore):
    texts = ["RSA is based on factoring.", "Elliptic Curve Cryptography."]
    vecs = [_vec(0.3), _vec(0.4)]
    store.add_texts(texts, vecs, memory_id="mem2", app="crypto")

    hits_bm25 = store.query_by_text("RSA", top_k=2, memory_id="mem2", app="crypto")
    assert any("RSA" in h["text"] for h in hits_bm25)

    hits_hybrid = store.query_by_text(
        "Elliptic Curve",
        top_k=2,
        hybrid=True,
        query_vector=_vec(0.4),
        memory_id="mem2",
        app="crypto",
    )
    assert any("Curve" in h["text"] for h in hits_hybrid)


def test_batch_upsert_and_replace(store: WeaviateStore):
    texts = ["to be updated", "stay the same"]
    vecs = [_vec(0.5), _vec(0.6)]
    ids = store.batch_upsert(texts, vecs, app="test", memory_id="mem3")
    assert len(ids) == 2

    ok = store.replace_one(
        ids[0], "updated text", _vec(0.55),
        metadata={"tag": "updated"},
        memory_id="mem3", app="test"
    )
    assert ok is True

    hits = store.search(_vec(0.55), top_k=5, memory_id="mem3", app="test")
    assert any("updated text" in h["text"] for h in hits)


def test_delete(store: WeaviateStore):
    texts = ["to be deleted"]
    vecs = [_vec(0.7)]
    ids = store.add_texts(texts, vecs, app="test", memory_id="mem4")
    uid = ids[0]

    assert store.delete(uid) is True

    # 验证对象确实被删除
    hits = store.search(_vec(0.7), top_k=5, memory_id="mem4", app="test")
    assert all(h["id"] != uid for h in hits)


def test_list_collections(store: WeaviateStore):
    cols = store.list_collections()
    cols_norm = [c.replace("_", "").lower() for c in cols]
    assert TEST_COLLECTION.replace("_", "").lower() in cols_norm
