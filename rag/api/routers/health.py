# 健康检查与依赖自检（连通 Weaviate/MinIO/LLM）

from fastapi import APIRouter, Depends
from rag.api.deps import get_settings, Settings
from rag.core.pipeline import Pipeline
from rag.datasource.connections.weaviate_connection import WeaviateConnection
from rag.datasource.connections.minio_connection import MinioConnection
from rag.utils.logging import get_logger
from datetime import datetime

router = APIRouter()
logger = get_logger(__name__)

@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    # Service 基本信息
    service_info = {
        "service": settings.service_name,
        "version": settings.service_version,
        "env": settings.rag_env,
        "time": datetime.utcnow().isoformat() + "Z",
    }

    # Weaviate 健康检查
    weaviate_conn = WeaviateConnection(
        scheme=settings.weaviate_scheme,
        host=settings.weaviate_host,
        port=settings.weaviate_port,
        grpc_port=settings.weaviate_grpc_port,
    )
    weaviate_health = weaviate_conn.health(enabled=settings.weaviate_enabled)

    # MinIO 健康检查
    minio_conn = MinioConnection(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    minio_health = minio_conn.health(enabled=settings.minio_enabled)

    # MVP Pipeline 烟囱测试（不调用任何外部服务）
    pipeline = Pipeline()
    pipeline_probe = pipeline.run("ping")

    result = {
        **service_info,
        "dependencies": {
            "weaviate": weaviate_health.__dict__,
            "minio": minio_health.__dict__,
        },
        "pipeline_probe": pipeline_probe,
    }
    logger.info("health checked: %s", result)
    return result
