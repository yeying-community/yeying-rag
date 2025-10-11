# -*- coding: utf-8 -*-
"""
JD 检索模块（面试官场景）
---------------------------------
功能：
1. 输入自然语言查询，检索 JD 知识库（InterviewerJDKnowledge）
2. 支持 top_k 限制、可选公司过滤
3. 返回结构化岗位信息及相似度分数
"""
# # ===== Test 用，正常不加载 =====
# from dotenv import load_dotenv
# load_dotenv(override=True)
# # ===== Test 用，正常不加载 =====

from typing import List, Dict, Optional
from rag.datasource.vectorstores.weaviate_store import WeaviateStore
from rag.llm.embeddings.openai_embedding import OpenAIEmbedder
from weaviate.classes.query import Filter


class JDRetriever:
    """
    JD 检索器（面试官场景）
    ---------------------------------
    示例：
        retriever = JDRetriever()
        retriever.search("阿里安全算法岗位职责", top_k=5)
    """

    def __init__(
        self,
        collection: str = "InterviewerJDKnowledge",
        company: Optional[str] = None
    ):
        # 初始化向量库和 embedder
        self.store = WeaviateStore(collection=collection)
        self.embedder = OpenAIEmbedder()
        self.company = company  # 可选：限定公司检索

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        在 JD 知识库中进行语义检索
        :param query: 用户查询文本
        :param top_k: 返回条数
        """
        emb = self.embedder.embed_query(query)
        col = self.store.client.collections.get(self.store.collection)

        # 可选公司过滤
        filters = None
        if self.company:
            filters = Filter.by_property("company").equal(self.company)

        # 执行向量检索
        result = col.query.near_vector(
            near_vector=emb,
            limit=top_k,
            filters=filters,
            return_properties=[
                "job_id", "company", "position", "category",
                "requirements", "description", "location"
            ]
        )

        # 处理结果
        hits = []
        for obj in result.objects:
            p = obj.properties
            hits.append({
                "job_id": p.get("job_id"),
                "company": p.get("company"),
                "position": p.get("position"),
                "category": p.get("category"),
                "requirements": p.get("requirements"),
                "description": p.get("description"),
                "location": p.get("location"),
            })

        return hits


if __name__ == "__main__":
    retriever = JDRetriever()
    results = retriever.search("推荐系统算法岗位职责", top_k=3)
    print(results)
    print("\n🔍 JD 检索结果：")
    for r in results:
        print(f"- [{r['company']}] {r['position']}")
        print(f"  要求: {r['requirements'][:80]}...")
        print(f"  地址：{r['location']}")
