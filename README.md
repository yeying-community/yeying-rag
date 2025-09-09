# Yeying RAG


## 启动服务

### 方式一：使用启动脚本（推荐）

```bash
# 开发环境启动（默认端口：gRPC=9501, HTTP=8841）
./scripts/runner.sh -e dev

# 生产环境启动（默认端口：gRPC=9502, HTTP=8842）
./scripts/runner.sh -e prod

# 自定义端口启动
./scripts/runner.sh -e dev -g 9500 -h 8500

# 启用调试模式
./scripts/runner.sh -d -e dev
```

### 方式二：直接运行 Python

```bash
# 基础启动
PYTHONPATH=. python rag/runner.py --config config/config.yaml --env dev

# 指定端口启动
PYTHONPATH=. python rag/runner.py \
  --config config/config.yaml \
  --grpc-port 9501 \
  --http-port 8841 \
  --env dev

# 启用调试模式
PYTHONPATH=. python rag/runner.py --debug --config config/config.yaml --env dev
```

## 停止服务

```bash
# 正常停止服务
./scripts/stop.sh

# 强制停止所有相关进程
./scripts/stop.sh -f

# 停止指定进程
./scripts/stop.sh -p <PID>
```


## 测试

### 运行全部测试

```bash
# 运行所有测试
python -m pytest test/ -v

# 运行特定测试文件
python -m pytest test/test_config.py -v

# 运行测试并显示覆盖率
python -m pytest test/ -v --cov=rag
```

### 测试说明

- `test_config.py`：配置系统测试
- `test_database.py`：数据库连接和迁移测试  
- `test_models.py`：数据模型测试

## 端口说明

| 环境 | gRPC端口 | HTTP端口 |
|------|----------|----------|
| 开发环境 (dev) | 9501 | 8841 |
| 生产环境 (prod) | 9502 | 8842 |

## 日志文件

- 启动日志：`run/log/start.log`
- 应用日志：`run/log/rag.log`
- 进程ID：`run/pid.txt`
