from __future__ import annotations
from typing import Optional, Dict
from weaviate import connect_to_custom, WeaviateClient
from weaviate.classes.init import Auth
import httpx
from .common import HealthResult

class WeaviateConnection:
    def __init__(
        self,
        scheme: str,
        host: str,
        port: int,
        grpc_port: int,
        api_key: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.scheme = scheme
        self.host = host
        self.port = int(port)
        self.grpc_port = grpc_port
        self.secure = (scheme.lower() == "https")
        self.api_key = api_key or None
        self.extra_headers = extra_headers or {}
        self._client: Optional[WeaviateClient] = None

    @property
    def base_http(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"

    @property
    def client(self) -> WeaviateClient:
        if self._client is None:
            auth = Auth.api_key(self.api_key) if self.api_key else None
            # 传入 gRPC 参数（v4 必填），但跳过启动检查
            self._client = connect_to_custom(
                http_host=self.host,
                http_port=self.port,
                http_secure=self.secure,
                grpc_host=self.host,
                grpc_port=self.grpc_port,           # 随便给一个默认值；因为我们 skip_init_checks
                grpc_secure=self.secure,
                auth_credentials=auth,
                headers=self.extra_headers if self.extra_headers else None,
                skip_init_checks=True,     # 关键：不在初始化时做 gRPC/REST 的健康检查
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _rest_ready(self) -> HealthResult:
        url = f"{self.base_http}/v1/.well-known/ready"
        try:
            with httpx.Client(timeout=2.0) as s:
                r = s.get(url)
            if r.status_code == 200:
                return HealthResult(status="ok", details="rest ready")
            return HealthResult(status="error", details=f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            return HealthResult(status="error", details=str(e))

    def health(self, enabled: bool) -> HealthResult:
        if not enabled:
            return HealthResult(status="disabled", details="WEAVIATE_ENABLED=false")
        # 用 REST 健康检查，完全绕过 gRPC
        return self._rest_ready()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
