# 创建 FastAPI、挂路由、中间件（CORS/TraceID/速率限制）、全局异常处理。
from fastapi import FastAPI
from rag.api.deps import get_settings
from rag.api.routers.health import router as health_router
from rag.utils.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    description="YEYING-RAG · MVP",
)

# 注册路由
app.include_router(health_router)

# 根路由（可选）
@app.get("/")
def root():
    return {"message": "YEYING-RAG API is running", "version": settings.service_version}
