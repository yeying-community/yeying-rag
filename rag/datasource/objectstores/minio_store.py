# rag/datasource/objectstores/minio_store.py
from __future__ import annotations
import os, io
import json
import datetime, uuid
from typing import Optional, List
from minio.error import S3Error

from ..connections.common import HealthResult
from ..connections.minio_connection import MinioConnection


class MinIOStore:
    """
    MinIO 简易封装（基于 MinioConnection）：
    - 统一经由 MinioConnection.client 获取 MinIO 客户端
    - 保留文件型 API（upload_file/download_file/delete_file/list_files）
    - 提供便捷字节/文本 API（put_bytes/put_text/get_object）
    - 暴露 default_bucket，供主记忆等默认写入
    """

    def __init__(
        self,
        conn: MinioConnection,
        default_bucket: Optional[str] = None,
    ):
        self.conn = conn
        self.default_bucket = default_bucket or os.getenv("MINIO_BUCKET_KB", "yeying-primary-memory")
        # 幂等确保默认桶存在
        try:
            if not self.conn.client.bucket_exists(self.default_bucket):
                self.conn.client.make_bucket(self.default_bucket)
        except Exception:
            pass

    # 便捷访问
    @property
    def client(self):
        return self.conn.client

    # ---------- Bucket ----------
    def create_bucket(self, bucket_name: str) -> None:
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to create bucket {bucket_name}: {e}")

    def delete_bucket(self, bucket_name: str) -> None:
        try:
            for obj in self.client.list_objects(bucket_name, recursive=True):
                self.client.remove_object(bucket_name, obj.object_name)
            self.client.remove_bucket(bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to delete bucket {bucket_name}: {e}")

    # ---------- Object（文件型） ----------
    def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        object_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        try:
            object_name = object_name or os.path.basename(file_path)
            self.client.fput_object(bucket_name, object_name, file_path, content_type=content_type)
            return object_name
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to {bucket_name}: {e}")

    def download_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
        try:
            self.client.fget_object(bucket_name, object_name, file_path)
        except S3Error as e:
            raise RuntimeError(f"Failed to download file from {bucket_name}: {e}")

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        try:
            self.client.remove_object(bucket_name, object_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to delete file from {bucket_name}: {e}")

    def list_files(self, bucket_name: str, prefix: str = "", recursive: bool = True) -> List[str]:
        try:
            return [o.object_name for o in self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)]
        except S3Error as e:
            raise RuntimeError(f"Failed to list files from {bucket_name}: {e}")

    # ---------- 便捷 Bytes/Text API（主记忆在用） ----------
    def put_bytes(self, key: str, data: bytes, bucket: Optional[str] = None, content_type: Optional[str] = None) -> str:
        bkt = bucket or self.default_bucket
        self.client.put_object(bkt, key, io.BytesIO(data), length=len(data), content_type=content_type)
        return key

    def put_text(self, key: str, text: str, bucket: Optional[str] = None, content_type: str = "text/plain; charset=utf-8") -> str:
        return self.put_bytes(key=key, data=text.encode("utf-8"), bucket=bucket, content_type=content_type)

    def get_object(self, bucket: Optional[str], key: str):
        bkt = bucket or self.default_bucket
        return self.client.get_object(bkt, key)

    def get_bytes(self, key: str, bucket: Optional[str] = None) -> bytes:
        """
        读取对象并以 bytes 返回；内部负责安全关闭流。
        """
        bkt = bucket or self.default_bucket
        resp = self.client.get_object(bkt, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def get_text(self, key: str, bucket: Optional[str] = None, encoding: str = "utf-8") -> str:
        """
        读取对象并解码为字符串；默认 utf-8。
        """
        data = self.get_bytes(key, bucket=bucket)
        return data.decode(encoding)

    def put_json(self, key: str, obj, bucket: Optional[str] = None) -> str:
        """
        将 Python 对象以 JSON 存入 MinIO；设置 content-type = application/json。
        """
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        return self.put_bytes(
            key=key,
            data=data,
            bucket=bucket,
            content_type="application/json; charset=utf-8",
        )

    def get_json(self, key: str, bucket: Optional[str] = None):
        """
        读取对象并反序列化为 Python 对象；若 JSON 格式错误，抛出 RuntimeError。
        """
        text = self.get_text(key, bucket=bucket)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in object '{key}': {e}") from e

    def exists(self, key: str, bucket: Optional[str] = None) -> bool:
        """
        检查对象是否存在，存在返回 True，否则 False。
        """
        bkt = bucket or self.default_bucket
        try:
            self.client.stat_object(bkt, key)
            return True
        except Exception:
            return False

    def make_key(self, app: str, memory_id: str, filename: Optional[str] = None, ext: Optional[str] = None) -> str:
        """
        生成符合规范的对象 key：
        - app/memory_id/{timestamp}_{uuid}[.ext]
        - 如果提供 filename，则直接拼接成 app/memory_id/filename
        """
        prefix = f"{app}/{memory_id}"
        if filename:
            return f"{prefix}/{filename}"

        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = uuid.uuid4().hex[:8]
        name = f"{ts}_{uid}"
        if ext:
            name = f"{name}.{ext.lstrip('.')}"
        return f"{prefix}/{name}"


    # ---------- Health（复用连接的健康检查） ----------
    def health(self, enabled: bool = True) -> HealthResult:
        return self.conn.health(enabled)
