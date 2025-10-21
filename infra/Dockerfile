# ==========================
# yeying-rag production image
# ==========================
FROM python:3.11-slim

WORKDIR /app

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app \
    PORT=8001

# ---------- 安装系统依赖 ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# ---------- 拷贝代码 ----------
COPY pyproject.toml ./
COPY rag ./rag
COPY infra ./infra
COPY requirements.txt ./requirements.txt
COPY .env.example ./

# ---------- 安装依赖 ----------
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-warn-script-location -r requirements.txt

# ---------- 启动前初始化脚本 ----------
# 创建入口脚本
RUN echo '#!/usr/bin/env bash\n' \
         'set -e\n' \
         'echo "🔧 初始化 JD collection..."\n' \
         'python infra/scripts/init_weaviate_jd.py || echo "⚠️ 初始化失败或已存在，继续启动"\n' \
         'echo "🚀 启动 FastAPI 服务..."\n' \
         'exec uvicorn rag.api.main:app --host 0.0.0.0 --port ${PORT:-8001}\n' \
    > /app/entrypoint.sh \
 && chmod +x /app/entrypoint.sh

EXPOSE 8001

# ---------- 启动 ----------
CMD ["/app/entrypoint.sh"]
