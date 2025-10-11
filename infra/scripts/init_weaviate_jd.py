# -*- coding: utf-8 -*-
"""
初始化 InterviewerJDKnowledge schema
"""
# # ===== Test 用，正常不加载 =====
# from dotenv import load_dotenv
# load_dotenv(override=False)
# # ===== Test 用，正常不加载 =====

import os
import weaviate
import weaviate.classes.config as wc
from rag.datasource.connections.weaviate_connection import WeaviateConnection


def init_jd_collection():
    conn = WeaviateConnection(
        scheme=os.getenv("WEAVIATE_SCHEME", "http"),
        host=os.getenv("WEAVIATE_HOST", "localhost"),
        port=int(os.getenv("WEAVIATE_PORT", "8080")),
        grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
        api_key=os.getenv("WEAVIATE_API_KEY"),
    )
    client: weaviate.WeaviateClient = conn.client

    name = "InterviewerJDKnowledge"

    try:
        existing = client.collections.list_all()
        if name in existing:
            print(f"✅ Collection {name} 已存在")
            return
    except Exception:
        pass

    props = [
        wc.Property(name="job_id", data_type=wc.DataType.TEXT, description="岗位唯一ID"),
        wc.Property(name="company", data_type=wc.DataType.TEXT, description="公司名称"),
        wc.Property(name="position", data_type=wc.DataType.TEXT, description="岗位名称"),
        wc.Property(name="category", data_type=wc.DataType.TEXT_ARRAY, description="岗位类别标签"),
        wc.Property(name="department", data_type=wc.DataType.TEXT, description="部门/事业部"),
        wc.Property(name="product", data_type=wc.DataType.TEXT, description="产品线"),
        wc.Property(name="location", data_type=wc.DataType.TEXT_ARRAY, description="工作地点"),
        wc.Property(name="education", data_type=wc.DataType.TEXT, description="学历要求"),
        wc.Property(name="experience", data_type=wc.DataType.TEXT, description="工作年限"),

        wc.Property(name="requirements", data_type=wc.DataType.TEXT, description="岗位要求"),
        wc.Property(name="description", data_type=wc.DataType.TEXT, description="岗位描述"),
        wc.Property(name="content", data_type=wc.DataType.TEXT, description="拼接文本（向量化内容）"),

        wc.Property(name="hash", data_type=wc.DataType.TEXT, description="内容哈希值，用于检测变化"),
        wc.Property(name="status", data_type=wc.DataType.TEXT, description="岗位状态：active / expired"),

        wc.Property(name="publishDate", data_type=wc.DataType.DATE, description="发布时间"),
        wc.Property(name="crawlerDate", data_type=wc.DataType.DATE, description="爬取时间（crawl_date）"),
        wc.Property(name="vectorizedAt", data_type=wc.DataType.DATE, description="向量化时间"),

        wc.Property(name="extra", data_type=wc.DataType.TEXT, description="扩展字段（JSON）"),
        wc.Property(name="sourceBucket", data_type=wc.DataType.TEXT, description="MinIO 源桶"),
        wc.Property(name="sourceKey", data_type=wc.DataType.TEXT, description="MinIO 对象 key"),
    ]

    client.collections.create(
        name=name,
        properties=props,
        vector_config=wc.Configure.Vectors.self_provided(),
    )
    print(f"🎉 成功创建 Collection {name}")

if __name__ == "__main__":
    init_jd_collection()
