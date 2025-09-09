from minio import Minio
from minio.error import S3Error
import io

class MinioClient:
    def __init__(self, config):
        """初始化 MinIO 客户端"""
        self.client = Minio(
            config["domain"],
            access_key=config["access_key"],
            secret_key=config["secret_key"],
            secure=config["tls"]
        )

    def list_buckets(self):
        """列出所有存储桶"""
        try:
            return self.client.list_buckets()
        except S3Error as e:
            print(f"❌ MinIO 错误: {e}")
            return None

    def create_bucket(self, bucket_name):
        """创建存储桶"""
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                print(f"✅ 存储桶 '{bucket_name}' 创建成功")
            else:
                print(f"ℹ 存储桶 '{bucket_name}' 已存在")
        except S3Error as e:
            print(f"❌ MinIO 错误: {e}")

    def upload_file(self, bucket_name, file_name, file_content):
        """上传文件到存储桶"""
        try:
            file = io.BytesIO(file_content.encode('utf-8'))
            self.client.put_object(
                bucket_name,
                file_name,
                file,
                length=len(file_content),
                content_type="text/plain"
            )
            print(f"✅ 文件 '{file_name}' 上传成功")
        except S3Error as e:
            print(f"❌ MinIO 错误: {e}")

    def download_file(self, bucket_name, file_name):
        """从存储桶下载文件"""
        try:
            response = self.client.get_object(bucket_name, file_name)
            content = response.read().decode('utf-8')
            response.close()
            return content
        except S3Error as e:
            print(f"❌ MinIO 错误: {e}")
            return None

    def list_objects(self, bucket_name):
        """列出存储桶中的对象"""
        try:
            return self.client.list_objects(bucket_name)
        except S3Error as e:
            print(f"❌ MinIO 错误: {e}")
            return None

    def generate_presigned_url(self, bucket_name, file_name, expiration=3600):
        """生成文件的预签名 URL"""
        try:
            from datetime import timedelta
            return self.client.presigned_get_object(bucket_name, file_name, expires=timedelta(seconds=expiration))
        except S3Error as e:
            print(f"❌ MinIO 错误: {e}")
            return None
