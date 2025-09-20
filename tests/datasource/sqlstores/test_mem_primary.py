# -*- coding: utf-8 -*-
import os, uuid
import pytest

from rag.datasource.sqlstores.mem_primary_store import MemPrimaryStore
from rag.datasource.connections.sqlite_connection import SQLiteConnection

# 为了避免污染正式 db，可以单独建一个临时测试库
TEST_DB_PATH = os.path.join(os.getcwd(), "db/rag_test.sqlite3")

@pytest.fixture(scope="module")
def store():
    conn = SQLiteConnection(TEST_DB_PATH)
    return MemPrimaryStore(conn)

def test_mem_primary_lifecycle(store: MemPrimaryStore):
    memory_id = f"m-{uuid.uuid4()}"

    # 初始化
    store.upsert(memory_id)
    row1 = store.get(memory_id)
    assert row1 is not None
    assert row1["total_qa_count"] == 0
    assert row1["recent_qa_count"] == 0

    # 累加 QA
    store.bump_total(memory_id, 3)
    row2 = store.get(memory_id)
    assert row2["total_qa_count"] == 3
    assert row2["recent_qa_count"] == 3

    # 更新摘要
    url = f"s3://bucket/{memory_id}/summary-v1.json"
    store.update_summary(memory_id, url)
    row3 = store.get(memory_id)
    assert row3["summary_url"] == url
    assert row3["summary_version"] == 1
    assert row3["recent_qa_count"] == 0  # 被清零

    # 推进索引
    store.advance_index(memory_id, 3)
    row4 = store.get(memory_id)
    assert row4["last_summary_index"] == 3
