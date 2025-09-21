# -*- coding: utf-8 -*-
import uuid, pytest
from rag.datasource.sqlstores.mem_deleted_store import MemDeletedStore

@pytest.fixture(scope="module")
def store():
    return MemDeletedStore()

def test_mark_and_check_deleted(store: MemDeletedStore):
    memory_id = f"mem-{uuid.uuid4()}"
    key = f"{memory_id}/dialogue_{uuid.uuid4().hex}.json"

    store.mark_deleted(memory_id, key)
    assert store.is_deleted(key) is True

def test_list_deleted(store: MemDeletedStore):
    memory_id = f"mem-{uuid.uuid4()}"
    key1 = f"{memory_id}/d1.json"
    key2 = f"{memory_id}/d2.json"

    store.mark_deleted(memory_id, key1)
    store.mark_deleted(memory_id, key2)

    rows = store.list_deleted(memory_id)
    keys = [r["key"] for r in rows]
    assert key1 in keys and key2 in keys
