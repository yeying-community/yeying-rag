# -*- coding: utf-8 -*-
import uuid, pytest
from rag.datasource.sqlstores.mem_registry_store import MemRegistryStore

@pytest.fixture(scope="module")
def store():
    return MemRegistryStore()

def test_mem_registry_upsert_and_get(store: MemRegistryStore):
    mid = f"m-{uuid.uuid4()}"
    app = "interviewer"

    store.upsert(mid, app, params={"aux_k": 5}, name="demo memory", owner="tester")
    row = store.get(mid)
    assert row is not None
    assert row["app"] == app
    assert '"aux_k": 5' in row["params_json"]

    # 更新 app + 参数
    store.upsert(mid, "grader", params={"primary_max_tokens": 200})
    row2 = store.get(mid)
    assert row2["app"] == "grader"
    assert '"primary_max_tokens": 200' in row2["params_json"]

def test_mem_registry_list(store: MemRegistryStore):
    rows = store.list_by_app("grader")
    assert isinstance(rows, list)
