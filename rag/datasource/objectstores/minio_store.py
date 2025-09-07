# rag/datasource/objectstores/minio_store.py

from __future__ import annotations
import os
from typing import Optional, List
from minio import Minio
from minio.error import S3Error

from ..connections.common import HealthResult
from ..connections.minio_connection import MinioConnection  # 如果你有统一连接类可用；没有就删这行
# 本文件以最小可用为主，直接用 Minio 客户端

class MinIOStore:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        # endpoint 建议写成 "host:9000" 或 "host:443"
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    # ---------- Bucket ----------
    def create_bucket(self, bucket_name: str) -> None:
        """创建桶（幂等）"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to create bucket {bucket_name}: {e}")

    def delete_bucket(self, bucket_name: str) -> None:
        """删除桶：先清空对象，再删桶"""
        try:
            # 清空对象（简单版：逐个删除）
            objects = self.client.list_objects(bucket_name, recursive=True)
            for obj in objects:
                self.client.remove_object(bucket_name, obj.object_name)

            # 清空分段上传的残留(可选)
            # multipart = self.client.list_incomplete_uploads(bucket_name, recursive=True)
            # for up in multipart:
            #     self.client.remove_incomplete_upload(bucket_name, up.object_name, up.upload_id)

            # 最后删除桶
            self.client.remove_bucket(bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to delete bucket {bucket_name}: {e}")

    # ---------- Object ----------
    def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        object_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """
        上传文件。
        - 若未指定 object_name，则默认使用本地文件名（basename），以满足你的测试期望。
        - 返回最终的 object_name。
        """
        try:
            if object_name is None:
                object_name = os.path.basename(file_path)

            self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )
            return object_name
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file to {bucket_name}: {e}")

    def download_file(self, bucket_name: str, object_name: str, file_path: str) -> None:
        """下载对象到本地路径"""
        try:
            self.client.fget_object(bucket_name, object_name, file_path)
        except S3Error as e:
            raise RuntimeError(f"Failed to download file from {bucket_name}: {e}")

    def delete_file(self, bucket_name: str, object_name: str) -> None:
        """删除对象"""
        try:
            self.client.remove_object(bucket_name, object_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to delete file from {bucket_name}: {e}")

    def list_files(self, bucket_name: str, prefix: str = "", recursive: bool = True) -> List[str]:
        """列出对象名列表"""
        try:
            objs = self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive)
            return [o.object_name for o in objs]
        except S3Error as e:
            raise RuntimeError(f"Failed to list files from {bucket_name}: {e}")

    # ---------- Health ----------
    def health(self, enabled: bool = True) -> HealthResult:
        """最简健康检查：尝试 list_buckets；兼容 enabled 参数。"""
        if not enabled:
            return HealthResult(status="disabled", details="MINIO_ENABLED=false")
        try:
            _ = list(self.client.list_buckets())
            return HealthResult(status="ok", details="list_buckets ok")
        except Exception as e:
            return HealthResult(status="error", details=str(e))