# -*- coding: utf-8 -*-
"""
JDWorker
---------
从 MinIO 读取 JD JSON -> 生成向量 -> 写入 Weaviate

特性：
1. 支持 manifest 文件批量同步（含 crawl_date）
2. 增量更新：按 job_id + hash 检查是否变化
3. 下架删除：若 status == "expired" 自动删除
4. 记录时间戳（publishDate、crawlerDate、vectorizedAt）
"""
# ===== Test 用，正常不加载 =====
from dotenv import load_dotenv
load_dotenv(override=True)
# ===== Test 用，正常不加载 =====


import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional


from tqdm import tqdm
from rag.datasource.connections.minio_connection import MinioConnection
from rag.datasource.objectstores.minio_store import MinIOStore
from rag.datasource.vectorstores.weaviate_store import WeaviateStore
from rag.llm.embeddings.openai_embedding import OpenAIEmbedder
from rag.core.schemas import JDItem
from weaviate.classes.query import Filter




class JDWorker:
    def __init__(
        self,
        bucket: str = "company-jd",
        collection: str = "InterviewerJDKnowledge",
    ):
        """初始化依赖"""
        self.minio = MinIOStore(
            MinioConnection(
                endpoint=os.getenv("MINIO_ENDPOINT"),
                access_key=os.getenv("MINIO_ACCESS_KEY"),
                secret_key=os.getenv("MINIO_SECRET_KEY"),
                secure=os.getenv("MINIO_SECURE", "true").lower() == "true",
            )
        )
        self.weaviate = WeaviateStore(collection=collection)
        self.embedder = OpenAIEmbedder()
        self.bucket = bucket
        self.collection = collection

    # ===================== 基础方法 =====================

    def _compose_text(self, jd: JDItem) -> str:
        """拼接 JD 文本内容（用于 embedding）"""
        exp = f"{jd.experience}年以上经验" if jd.experience else ""
        edu = jd.education or ""
        return (
            f"公司：{jd.company}\n"
            f"职位：{jd.position}\n"
            f"类别：{'、'.join(jd.category)}\n"
            f"地点：{'、'.join(jd.location)}\n"
            f"经验要求：{exp}\n"
            f"学历要求：{edu}\n"
            f"岗位要求：{jd.requirements}\n"
            f"岗位描述：{jd.description}"
        )

    def _to_rfc3339(self, date_str: str | None) -> str | None:
        """确保日期是 RFC3339 格式"""
        if not date_str:
            return None
        try:
            # 若为 YYYYMMDD（如 20251007）
            if date_str.isdigit() and len(date_str) == 8:
                dt = datetime.strptime(date_str, "%Y%m%d")
                return dt.strftime("%Y-%m-%dT00:00:00Z")
            # 若为 YYYY-MM-DD
            if len(date_str) == 10 and date_str.count("-") == 2:
                return f"{date_str}T00:00:00Z"
            # 若已为 ISO 格式但无 Z
            if "T" in date_str and "Z" not in date_str:
                return f"{date_str}Z"
            return date_str
        except Exception:
            return None

    def _embed(self, text: str):
        """生成向量"""
        return self.embedder.embed_query(text)

    def _exists_and_same_hash(self, job_id: str, new_hash: str) -> Optional[str]:
        """检查 Weaviate 中是否已存在该 JD，若存在返回旧 hash"""
        col = self.weaviate.client.collections.get(self.collection)
        res = col.query.fetch_objects(
            filters=Filter.by_property("job_id").equal(str(job_id)),
            limit=1,
            return_properties=["hash"],
        )
        if not res.objects:
            return None
        old_hash = res.objects[0].properties.get("hash")
        return old_hash

    def _delete_by_job_id(self, job_id: str):
        """根据 job_id 删除 JD"""
        col = self.weaviate.client.collections.get(self.collection)
        col.data.delete_many(where=Filter.by_property("job_id").equal(str(job_id)))
        print(f"🗑 已删除下架 JD job_id={job_id}")

    # ===================== 主流程 =====================

    def _upsert_one(self, jd: JDItem, key: str, crawl_date: Optional[str] = None):
        """
        入库单个 JD，带增量检测：
        - 若 job_id 存在且 hash 一致 → 跳过
        - 若 hash 不同 → replace
        - 若不存在 → insert
        """
        # 处理删除情况
        status = getattr(jd, "status", None) or "active"
        if status.lower() == "expired":
            self._delete_by_job_id(jd.job_id)
            return

        # 增量检测
        old_hash = self._exists_and_same_hash(jd.job_id, jd.hash)
        if old_hash and old_hash == jd.hash:
            print(f"⏭ 未变化 job_id={jd.job_id}（hash 一致），跳过")
            return

        text = self._compose_text(jd)
        vector = self._embed(text)

        # 构建入库属性
        props = {
            "job_id": str(jd.job_id),
            "company": jd.company,
            "position": jd.position,
            "category": jd.category,
            "department": jd.department,
            "product": jd.product,
            "location": jd.location,
            "education": jd.education,
            "experience": str(jd.experience) if jd.experience else None,
            "requirements": jd.requirements,
            "description": jd.description,
            "content": f"{jd.requirements}\n{jd.description}",
            "hash": jd.hash,
            "status": status,
            "sourceBucket": self.bucket,
            "sourceKey": key,
            "publishDate": jd.extra.get("publish_date") if jd.extra else jd.publish_time,
            "crawlerDate": self._to_rfc3339(crawl_date or (jd.extra.get("crawl_date") if jd.extra else None)),
            "vectorizedAt": datetime.now(timezone.utc).isoformat(),  # ✅ 自动带 Z 时区
        }

        col = self.weaviate.client.collections.get(self.collection)

        # replace / insert 逻辑
        if old_hash and old_hash != jd.hash:
            # hash 变化：执行 replace
            res = col.query.fetch_objects(
                filters=Filter.by_property("job_id").equal(str(jd.job_id)),
                limit=1,
                return_properties=["_id"]
            )
            if res.objects:
                uid = str(res.objects[0].uuid)
                col.data.replace(uuid=uid, properties=props, vector=vector)
                print(f"♻️ 已更新 job_id={jd.job_id}（内容变化）")
                return

        # 新增
        col.data.insert(properties=props, vector=vector)
        print(f"✅ 已入库 job_id={jd.job_id} - {jd.position}")

    # ===================== Manifest 批量同步 =====================

    def sync_from_manifest(self, manifest_key: str):
        """读取 manifest 文件并执行同步"""
        manifest = self.minio.get_json(bucket=self.bucket, key=manifest_key)
        company = manifest.get("company")
        crawl_date = manifest.get("crawl_date")
        files = manifest.get("files", [])

        print(f"🚀 开始同步 [{company}] {crawl_date}，共 {len(files)} 条 JD")

        for item in tqdm(files, desc=f"同步 {company}-{crawl_date}"):
            job_id = item.get("job_id")
            key = item.get("key")

            try:
                jd_data = self.minio.get_json(bucket=self.bucket,key= key)
                # 自动补 company / crawl_date
                jd_data.setdefault("company", company)
                # 如果 extra 是 None，就重建一个 dict
                if not isinstance(jd_data.get("extra"), dict):
                    jd_data["extra"] = {}

                jd_data["extra"]["crawl_date"] = crawl_date
                # 类型规范化
                if isinstance(jd_data.get("job_id"), int):
                    jd_data["job_id"] = str(jd_data["job_id"])
                if isinstance(jd_data.get("experience"), int):
                    jd_data["experience"] = str(jd_data["experience"])

                # ✅ category: str → [str]
                if isinstance(jd_data.get("category"), str):
                    jd_data["category"] = [jd_data["category"]]
                elif jd_data.get("category") is None:
                    jd_data["category"] = []

                # ✅ location: str → [str]
                if isinstance(jd_data.get("location"), str):
                    jd_data["location"] = [jd_data["location"]]
                elif jd_data.get("location") is None:
                    jd_data["location"] = []

                # ✅ position: None → ""
                if isinstance(jd_data.get("position"), list):
                    jd_data["position"] = "、".join(jd_data["position"])
                elif jd_data.get("position") is None:
                    jd_data["position"] = ""

                jd = JDItem(**jd_data)

                self._upsert_one(jd, key, crawl_date)
            except Exception as e:
                print(f"⚠️ {job_id} ({key}) 同步失败: {e}")

        print(f"🎉 [{company}] {crawl_date} 同步完成")


if __name__ == "__main__":
    worker = JDWorker()
    # 示例：同步 2025-10-07 阿里巴巴 JD
    worker.sync_from_manifest("tencent/20251017/manifest.json")
