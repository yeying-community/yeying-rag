
# RAG 服务接口文档
## 如何启动服务
如何启动服务

1.构建 Docker 镜像：

 docker build -t yeying-rag:latest -f infra/Dockerfile .

启动 Docker 容器：

使用以下命令启动容器，映射本地端口和容器端口：

docker run -d --name yeying-rag --env-file .env --network host yeying-rag:latest

这将会把容器的 8001 端口映射到主机的 8001 端口。 


## 1. 健康检查接口：`/health`

### 功能
该接口用于检查服务的健康状态，包括服务版本、环境设置，以及外部依赖（如 Weaviate 和 MinIO）的健康状况。

### 请求方法
`GET`

### 请求示例
```bash
curl -X GET http://localhost:5000/health
```

### 响应示例
```json
{
  "service": "yeying-rag",
  "version": "0.1.0",
  "env": "dev",
  "time": "2025-10-19T12:39:20.197659Z",
  "dependencies": {
    "weaviate": {
      "status": "ok",
      "details": "Weaviate is up and running."
    },
    "minio": {
      "status": "ok",
      "details": "MinIO is operational."
    }
  }
}
```

### 说明
- **Weaviate** 和 **MinIO** 的状态会根据服务配置的健康检查结果返回，若服务未启用，则显示为 `"disabled"`。

---

## 2. 创建记忆接口：`/memory/create`

### 功能
用于创建新的记忆空间，返回 `memory_id`，为后续的推送和查询消息提供一个唯一标识符。

### 请求方法
`POST`

### 请求参数
- `app`: 应用名（如：`test_app`）。
- `params`: 包含摘要和检索的参数（如 `summary_every_n`, `max_summary_tokens`, `top_k`）。

### 请求示例
```bash
curl -X POST http://localhost:5000/memory/create -H "Content-Type: application/json" -d '{
  "app": "test_app",
  "params": {
    "summary_every_n": 3,
    "max_summary_tokens": 500,
    "top_k": 5
  }
}'
```

### 响应示例
```json
{
  "memory_id": "test_app_e25fac3b08d2"
}
```

### 说明
- 创建记忆空间后，`memory_id` 将作为后续操作（如推送和查询）中的标识符。

---

## 3. 推送消息接口：`/memory/push`

### 功能
向指定的记忆空间推送消息，用于存储对话或其他数据。

### 请求方法
`POST`

### 请求参数
- `memory_id`: 记忆空间 ID。
- `app`: 应用名称。
- `url`: 消息的 URL 或唯一标识符。
- `description`: 消息内容。

### 请求示例
```bash
curl -X POST http://localhost:5000/memory/push -H "Content-Type: application/json" -d '{
  "memory_id": "test_app_e25fac3b08d2",
  "app": "test_app",
  "url": "http://example.com",
  "description": "This is a test message."
}'
```

### 响应示例
```json
{
  "status": "ok",
  "row": 1
}
```

### 说明
- 消息成功推送后，返回 `status: "ok"` 和推送的行数（`row`）。

---

## 4. 查询记忆接口：`/query`

### 功能
查询指定记忆空间中的数据，根据不同模式返回问答或生成面试题。

### 请求方法
`POST`

### 请求参数
- `query`: 用户的查询内容。
- `memory_id`: 记忆空间 ID。
- `app`: 应用模式（如 `default` 或 `interviewer`）。
- `company`, `target_position`, `jd_top_k`, `memory_top_k`: 仅在面试官模式下使用，定义面试相关的参数。

### 请求示例
```bash
curl -X POST http://localhost:5000/query -H "Content-Type: application/json" -d '{
  "query": "What is the capital of France?",
  "memory_id": "test_app_e25fac3b08d2",
  "app": "default"
}'
```

### 响应示例
```json
{
  "answer": "The capital of France is Paris.",
  "context_used": "Some context data used to generate the answer."
}
```

### 说明
- 在 `app = "interviewer"` 模式下，接口会生成面试题并返回相关的面试问题；在默认模式下，提供一般的问答功能。

---
