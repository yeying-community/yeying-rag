from typing import Optional
from minio import Minio
from .common import HealthResult

class MinioConnection:
    """
    MVP：通过 list_buckets() 做连通性探测。
    注意：若账号无权限或服务器未启动，会抛异常 → 捕获并返回 error。
    """
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool) -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def health(self, enabled: bool) -> HealthResult:
        if not enabled:
            return HealthResult(status="disabled", details="MINIO_ENABLED=false")

        try:
            # 只要能列出 buckets，就当连通正常；即便为空列表也算 ok
            _ = self.client.list_buckets()
            return HealthResult(status="ok", details="list_buckets ok")
        except Exception as e:
            return HealthResult(status="error", details=str(e))
