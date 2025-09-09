# -*- coding: utf-8 -*-
import os
import time
import pytest

# 根据你的项目结构调整这两行导入路径：
from rag.datasource.vectorstores.weaviate_store import WeaviateStore, Doc
from rag.datasource.connections.weaviate_connection import WeaviateConnection


# =========================
# 环境参数（可通过环境变量覆盖）
# =========================
WEAVIATE_SCHEME = os.getenv("WEAVIATE_SCHEME", "http")
WEAVIATE_HOST = os.getenv("WEAVIATE_HOST", "test-weaviate.yeying.pub")
WEAVIATE_PORT = int(os.getenv("WEAVIATE_PORT", "8080"))
WEAVIATE_GRPC_PORT = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "") or None
WEAVIATE_TENANT = os.getenv("WEAVIATE_TENANT", "") or None

# 临时 collection / 业务标识
TEST_COLLECTION = os.getenv("WEAVIATE_TEST_COLLECTION", "TestRAGChunks_pytest")
TEST_MEMORY_KEY = "pytest_kb"
VEC_DIM = int(os.getenv("WEAVIATE_TEST_VEC_DIM", "16"))  # 确保与你的嵌入维度一致


@pytest.fixture(scope="session")
def weaviate_client():
    """建立真实的 Weaviate 连接；不可达则跳过整个测试文件。"""
    try:
        conn = WeaviateConnection(
            scheme=WEAVIATE_SCHEME,
            host=WEAVIATE_HOST,
            port=WEAVIATE_PORT,
            grpc_port=WEAVIATE_GRPC_PORT,
            api_key=WEAVIATE_API_KEY,
        )
        client = conn.client
        # 连接健康探测
        if not client.is_ready():
            pytest.skip("Weaviate client.is_ready() = False，跳过集成测试")
        yield client
    except Exception as e:
        pytest.skip(f"Weaviate 不可达：{e}")


@pytest.fixture
def store(weaviate_client):
    """创建临时 collection + 可选 tenant，测试结束后清理。"""
    s = WeaviateStore(
        client=weaviate_client,
        collection_name=TEST_COLLECTION,
        multi_tenancy=bool(WEAVIATE_TENANT),
        default_tenant=WEAVIATE_TENANT,
    )

    # 清理旧数据（按 memory_key）
    try:
        s.delete_by_filter(memory_key=TEST_MEMORY_KEY, tenant=WEAVIATE_TENANT)
    except Exception:
        pass

    yield s

    # 数据清理
    try:
        s.delete_by_filter(memory_key=TEST_MEMORY_KEY, tenant=WEAVIATE_TENANT)
    except Exception:
        pass

    # 可选择删除整个 collection（若你希望保留，则注释掉）
    try:
        weaviate_client.collections.delete(TEST_COLLECTION)
    except Exception:
        pass


def _vec(val: float, n: int = VEC_DIM):
    return [val] * n


def test_upsert_and_get(store):
    """写入两条并按 UUID 读取"""
    docs = [
        Doc(
            text="AES-GCM provides authenticated encryption (AEAD).",
            vector=_vec(0.11),
            memory_key=TEST_MEMORY_KEY,
            tags=["aes", "aead"],
            chunk_id=f"aes-{int(time.time())}",
            uuid="pytest-u1",
        ),
        Doc(
            text="Diffie-Hellman establishes a shared secret.",
            vector=_vec(0.22),
            memory_key=TEST_MEMORY_KEY,
            tags=["dh"],
            chunk_id=f"dh-{int(time.time())}",
            uuid="pytest-u2",
        ),
    ]
    store.upsert(docs, tenant=WEAVIATE_TENANT)

    r1 = store.get_by_id("pytest-u1", tenant=WEAVIATE_TENANT)
    r2 = store.get_by_id("pytest-u2", tenant=WEAVIATE_TENANT)

    assert r1 is not None and "AEAD" in r1.text
    assert r2 is not None and "shared secret" in r2.text


def test_search_near_vector(store):
    """向量近邻检索"""
    docs = [
        Doc(
            text="Elliptic Curve Diffie-Hellman (ECDH) is used for key agreement.",
            vector=_vec(0.33),
            memory_key=TEST_MEMORY_KEY,
            uuid="pytest-nn-1",
        ),
        Doc(
            text="RSA relies on integer factorization hardness.",
            vector=_vec(0.44),
            memory_key=TEST_MEMORY_KEY,
            uuid="pytest-nn-2",
        ),
    ]
    store.upsert(docs, tenant=WEAVIATE_TENANT)

    hits = store.search_near_vector(
        vector=_vec(0.33),
        limit=2,
        memory_key=TEST_MEMORY_KEY,
        tenant=WEAVIATE_TENANT,
    )
    assert len(hits) >= 1
    # 至少能拿到文本和分数
    assert hits[0].text != ""
    assert isinstance(hits[0].score, float)


def test_search_hybrid(store):
    """Hybrid（BM25+向量）检索；不传向量时退化为 keyword-only"""
    docs = [
        Doc(
            text="AES-GCM is an AEAD mode that provides integrity and confidentiality.",
            vector=_vec(0.55),
            memory_key=TEST_MEMORY_KEY,
            uuid="pytest-h1",
        ),
        Doc(
            text="Completely unrelated content goes here.",
            vector=_vec(0.66),
            memory_key=TEST_MEMORY_KEY,
            uuid="pytest-h2",
        ),
    ]
    store.upsert(docs, tenant=WEAVIATE_TENANT)

    hits = store.search_hybrid(
        query="authenticated encryption",
        alpha=0.5,
        limit=5,
        memory_key=TEST_MEMORY_KEY,
        tenant=WEAVIATE_TENANT,
    )
    assert len(hits) >= 1
    assert "aes-gcm" in hits[0].text.lower() or "authenticated" in hits[0].text.lower()


def test_delete_by_ids(store):
    """按 UUID 删除"""
    doc = Doc(
        text="to-be-deleted",
        vector=_vec(0.77),
        memory_key=TEST_MEMORY_KEY,
        uuid="pytest-del-1",
    )
    store.upsert([doc], tenant=WEAVIATE_TENANT)
    assert store.get_by_id("pytest-del-1", tenant=WEAVIATE_TENANT) is not None

    n = store.delete_by_ids(["pytest-del-1"], tenant=WEAVIATE_TENANT)
    assert n == 1
    assert store.get_by_id("pytest-del-1", tenant=WEAVIATE_TENANT) is None


def test_delete_by_filter(store):
    """按过滤条件删除（memory_key）"""
    docs = [
        Doc(text="d1", vector=_vec(0.88), memory_key=TEST_MEMORY_KEY, uuid="pytest-f1"),
        Doc(text="d2", vector=_vec(0.99), memory_key=TEST_MEMORY_KEY, uuid="pytest-f2"),
    ]
    store.upsert(docs, tenant=WEAVIATE_TENANT)

    deleted = store.delete_by_filter(memory_key=TEST_MEMORY_KEY, tenant=WEAVIATE_TENANT)
    assert deleted >= 2  # 服务端统计；有时可能大于 2（包含之前插入的临时数据）


def test_health(store):
    """健康检查：is_ready + has_collection"""
    h = store.health()
    assert "status" in h and "details" in h
    assert h["status"] in ("ok", "error")
