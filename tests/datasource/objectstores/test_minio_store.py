# -*- coding: utf-8 -*-
import os, uuid, json, pytest
from rag.datasource.objectstores.minio_store import MinIOStore
from rag.datasource.connections.minio_connection import MinioConnection

@pytest.fixture(scope="module")
def minio_store():
    """MinIO 测试连接"""
    conn = MinioConnection(
        endpoint=os.getenv("MINIO_ENDPOINT", "test-minio.yeying.pub"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "zi3QOwIWYlu9JIpOeF0O"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "W4mAFU5tRU4FSvQKrY2up5XcJpAck2xkrqBt2giL"),
        secure=True,
    )
    store = MinIOStore(conn, default_bucket="test-bucket")
    store.create_bucket("test-bucket")  # 确保桶存在
    yield store
    store.delete_bucket("test-bucket")  # 测试结束后清理 bucket

# ---------- 文件型 API ----------

def test_upload_and_list_files(minio_store: MinIOStore):
    test_file_path = "/tmp/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test file.")

    minio_store.upload_file("test-bucket", test_file_path)
    files = minio_store.list_files("test-bucket")

    assert "test_file.txt" in files

    minio_store.delete_file("test-bucket", "test_file.txt")
    os.remove(test_file_path)

def test_download_file(minio_store: MinIOStore):
    test_file_path = "/tmp/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test file.")

    minio_store.upload_file("test-bucket", test_file_path)

    download_path = "/tmp/downloaded_test_file.txt"
    minio_store.download_file("test-bucket", "test_file.txt", download_path)

    with open(download_path, "r") as f:
        content = f.read()
    assert content == "This is a test file."

    minio_store.delete_file("test-bucket", "test_file.txt")
    os.remove(test_file_path)
    os.remove(download_path)

# ---------- Text / Bytes API ----------

def test_put_and_get_text(minio_store: MinIOStore):
    key = f"unittest/{uuid.uuid4().hex}.txt"
    text = "你好，RAG!"

    minio_store.put_text(key, text, bucket="test-bucket")
    result = minio_store.get_text(key, bucket="test-bucket")

    assert result == text

def test_put_and_get_bytes(minio_store: MinIOStore):
    key = f"unittest/{uuid.uuid4().hex}.bin"
    data = b"\x01\x02\x03"

    minio_store.put_bytes(key, data, bucket="test-bucket", content_type="application/octet-stream")
    result = minio_store.get_bytes(key, bucket="test-bucket")

    assert result == data

# ---------- JSON API ----------

def test_put_and_get_json(minio_store: MinIOStore):
    key = f"unittest/{uuid.uuid4().hex}.json"
    obj = {"hello": "world", "num": 42}

    minio_store.put_json(key, obj, bucket="test-bucket")
    result = minio_store.get_json(key, bucket="test-bucket")

    assert result == obj

def test_exists_and_make_key(minio_store: MinIOStore):
    memory_id = "mem-unittest"
    app = "interviewer"

    # 用 make_key 生成一个 key
    key = minio_store.make_key(app, memory_id, ext="json")
    obj = {"msg": "exists test"}
    minio_store.put_json(key, obj, bucket="test-bucket")

    assert minio_store.exists(key, bucket="test-bucket") is True

    # 不存在的 key
    fake_key = minio_store.make_key(app, memory_id, filename="not_exist.json")
    assert minio_store.exists(fake_key, bucket="test-bucket") is False

# ---------- 健康检查 ----------

def test_health(minio_store: MinIOStore):
    health = minio_store.health(True)
    assert health.status == "ok"
