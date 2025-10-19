# rag/api/routers/health.py
from fastapi import APIRouter, Depends
from datetime import datetime
from rag.api.deps import get_settings, Settings
from rag.datasource.connections.weaviate_connection import WeaviateConnection
from rag.datasource.connections.minio_connection import MinioConnection
from rag.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    result = {
        "service": settings.service_name,
        "version": settings.service_version,
        "env": settings.rag_env,
        "time": datetime.utcnow().isoformat() + "Z",
        "dependencies": {}
    }

    # ===== 检查 Weaviate =====
    if settings.weaviate_enabled:
        try:
            weaviate_conn = WeaviateConnection(
                scheme=settings.weaviate_scheme,
                host=settings.weaviate_host,
                port=settings.weaviate_port,
                grpc_port=settings.weaviate_grpc_port,
            )
            weaviate_health = weaviate_conn.health(enabled=settings.weaviate_enabled)
            result["dependencies"]["weaviate"] = weaviate_health.__dict__
        except Exception as e:
            result["dependencies"]["weaviate"] = {"status": "error", "details": str(e)}
    else:
        result["dependencies"]["weaviate"] = {"status": "disabled", "details": "WEAVIATE_ENABLED=false"}

    # ===== 检查 MinIO =====
    if settings.minio_enabled:
        try:
            minio_conn = MinioConnection(
                endpoint=settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            minio_health = minio_conn.health(enabled=settings.minio_enabled)
            result["dependencies"]["minio"] = minio_health.__dict__
        except Exception as e:
            result["dependencies"]["minio"] = {"status": "error", "details": str(e)}
    else:
        result["dependencies"]["minio"] = {"status": "disabled", "details": "MINIO_ENABLED=false"}

    logger.info("Health check result: %s", result)
    return result
