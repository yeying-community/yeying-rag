import os
import pytest
from rag.datasource.objectstores.minio_store import MinIOStore

@pytest.fixture
def minio_store():
    """MinIO 测试连接"""
    store = MinIOStore(
        endpoint=os.getenv("MINIO_ENDPOINT", "test-minio.yeying.pub"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "zi3QOwIWYlu9JIpOeF0O"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "W4mAFU5tRU4FSvQKrY2up5XcJpAck2xkrqBt2giL"),
        secure=True,  # 可根据实际需要设为 True
    )
    store.create_bucket("test-bucket")  # 先创建一个 bucket
    yield store
    store.delete_bucket("test-bucket")  # 测试结束后清理 bucket


def test_upload_and_list_files(minio_store):
    """测试文件上传与列出文件"""
    test_file_path = "/tmp/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test file.")

    # 上传文件
    minio_store.upload_file("test-bucket", test_file_path)

    # 列出存储桶内的文件
    files = minio_store.list_files("test-bucket")
    assert len(files) > 0  # 至少有一个文件
    assert "test_file.txt" in files

    # 清理测试文件
    minio_store.delete_file("test-bucket", "test_file.txt")


def test_download_file(minio_store):
    """测试文件下载"""
    test_file_path = "/tmp/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test file.")

    # 上传文件
    minio_store.upload_file("test-bucket", test_file_path)

    # 下载文件
    download_path = "/tmp/downloaded_test_file.txt"
    minio_store.download_file("test-bucket", "test_file.txt", download_path)

    # 验证文件内容
    with open(download_path, "r") as f:
        content = f.read()
    assert content == "This is a test file."

    # 清理
    os.remove(test_file_path)
    os.remove(download_path)
    minio_store.delete_file("test-bucket", "test_file.txt")


def test_delete_file(minio_store):
    """测试文件删除"""
    test_file_path = "/tmp/test_file.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a test file.")

    minio_store.upload_file("test-bucket", test_file_path)
    files = minio_store.list_files("test-bucket")
    assert "test_file.txt" in files

    # 删除文件
    minio_store.delete_file("test-bucket", "test_file.txt")
    files = minio_store.list_files("test-bucket")
    assert "test_file.txt" not in files

    os.remove(test_file_path)


def test_health(minio_store):
    """测试健康检查"""
    health = minio_store.health(True)
    print(health)
    assert health.status == "ok"
