from rag.datasource.weaviate_client import WeaviateClient


# 模拟 Weaviate 配置
config = {
    "url": "http://localhost:8080",  # Weaviate 实例的 URL
    "auth_token": None  # 如果需要认证，提供 Bearer Token
}

client = WeaviateClient(config)

# 1. 测试连接是否成功
if client.check_connection():
    # 2. 创建类
    client.create_class("my_collection")

    # 3. 存储向量
    vector_data = [0.1, 0.2, 0.3, 0.4, 0.5]  # 示例向量
    metadata = {"content": "这是一个示例内容", "source": "示例数据"}
    client.store_vector("my_collection", vector_data, metadata)

    # 4. 检索向量
    query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
    results = client.retrieve_vector("my_collection", query_vector)
    print("检索到的结果:", results)
else:
    print("❌ Weaviate 连接失败，无法进行其他操作。")