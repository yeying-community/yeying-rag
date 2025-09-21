from rag.datasource.sqlstores import MemContextsStore
import uuid, hashlib

store = MemContextsStore()

uid = str(uuid.uuid4())
h = hashlib.sha256(b"hello world").hexdigest()

row = store.create(
    uid=uid,
    memory_id="m1",
    app="interviewer",
    url="s3://yeying-rag/m1/ctx-0001.json",
    content_sha256=h,
    description="第一条上下文",
)
print("create:", row)

# 再次插入同一 hash（幂等）
row2 = store.create(
    uid=str(uuid.uuid4()),
    memory_id="m1",
    app="interviewer",
    url="s3://yeying-rag/m1/ctx-dup.json",
    content_sha256=h,
)
print("idempotent:", row2["uid"] == row["uid"])  # True

store.bump_qa(row["uid"], 2)
store.mark_summarized(row["uid"])
print("by_uid:", store.get_by_uid(row["uid"]))
print("list:", store.list_by_memory("m1", limit=5))
