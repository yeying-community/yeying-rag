from typing import Optional

from pydantic import BaseModel
from dotenv import load_dotenv
import os

# 加载 .env（只加载一次）
load_dotenv(override=False)

class Settings(BaseModel):
    service_name: str = os.getenv("SERVICE_NAME", "yeying-rag")
    service_version: str = os.getenv("SERVICE_VERSION", "0.1.0")
    rag_env: str = os.getenv("RAG_ENV", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Weaviate
    weaviate_enabled: bool = os.getenv("WEAVIATE_ENABLED", "false").lower() == "true"
    weaviate_scheme: str = os.getenv("WEAVIATE_SCHEME", "http")
    weaviate_host: str = os.getenv("WEAVIATE_HOST", "localhost")
    weaviate_port: int = int(os.getenv("WEAVIATE_PORT", "8080"))
    weaviate_grpc_port: int = os.getenv("WEAVIATE_GRPC_PORT", "50051")
    weaviate_api_key: Optional[str] = os.getenv("WEAVIATE_API_KEY") or None

    # MinIO
    minio_enabled: bool = os.getenv("MINIO_ENABLED", "false").lower() == "true"
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

_settings = Settings()

def get_settings() -> Settings:
    return _settings
