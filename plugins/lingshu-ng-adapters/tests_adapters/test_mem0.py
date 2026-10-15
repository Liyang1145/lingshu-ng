# -*- coding: utf-8 -*-
"""mem0 兼容 API：签名契约（对 mem0ai 2.2.1 签名快照逐参数核对；装了 mem0 时另与现装版本逐参数核对）+ 行为。"""
import asyncio
import inspect
import json
import os

import pytest

from lingshu_ng_adapters.mem0 import AsyncMemory, Memory, MemoryValidationError

SNAP = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "mem0_signatures.json"), encoding="utf-8"))
METHODS = ("add", "get", "get_all", "search", "update", "delete", "delete_all", "history", "reset")


def _sig(f):
    out = []
    for p in inspect.signature(f).parameters.values():
        d = p.default
        dv = "<required>" if d is inspect._empty else (repr(d) if isinstance(d, (str, int, float, bool, type(None)))
                                                         else "<sentinel>")
        out.append([p.name, p.kind.name, dv])
    return out


@pytest.mark.parametrize("cls", ["Memory", "AsyncMemory"])
@pytest.mark.parametrize("name", METHODS)
def test_signature_matches_mem0_snapshot(cls, name):
    """每个 mem0 方法：同名、形参名 / 种类 / 缺省值与 mem0ai 2.2.1 完全一致，同步 / 异步一致。"""
    ours = {"Memory": Memory, "AsyncMemory": AsyncMemory}[cls]
    want = SNAP[cls][name]
    assert _sig(getattr(ours, name)) == want["params"], (cls, name)
    assert inspect.iscoroutinefunction(getattr(ours, name)) == want["async"]


def test_signature_matches_installed_mem0_if_present():
    """装了 mem0ai 就与现装版本逐方法比对（没装 ⇒ skip；快照来源版本见 fixtures）。"""
    try:
        import mem0  # noqa: F401
        from mem0 import AsyncMemory as M0A
        from mem0 import Memory as M0
    except Exception as e:  # 第三方包导入失败类型不可枚举
        pytest.skip(f"mem0 不可用：{type(e).__name__}: {e}（快照 = mem0ai {SNAP['mem0ai']}）")
    for ours, theirs in ((Memory, M0), (AsyncMemory, M0A)):
        for n in METHODS:
            assert _sig(getattr(ours, n)) == _sig(getattr(theirs, n)), n


@pytest.fixture
def m(engine):
    return Memory(engine=engine)


def test_add_get_shapes(m):
    r = m.add("I love sci-fi movies", user_id="alice", metadata={"category": "movies"})
    assert list(r) == ["results"] and len(r["results"]) == 1
    item = r["results"][0]
    assert item["event"] == "ADD" and item["memory"] == "I love sci-fi movies"
    g = m.get(item["id"])
    assert set(g) >= {"id", "memory", "hash", "created_at", "updated_at", "user_id", "metadata"}
    assert g["user_id"] == "alice" and g["metadata"] == {"category": "movies"} and g["role"] == "user"
    assert m.get("no-such-id") is None


def test_add_message_forms(m):
    msgs = [{"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "I'm a vegetarian", "name": "alice_app"},
            {"role": "assistant", "content": [{"type": "text", "text": "Noted: no meat."}]}]
    r = m.add(msgs, user_id="alice")
    assert [x["memory"] for x in r["results"]] == ["I'm a vegetarian", "Noted: no meat."]
    g = m.get(r["results"][0]["id"])
    assert g["actor_id"] == "alice_app"
    assert m.add({"role": "user", "content": "dict form"}, agent_id="bot")["results"][0]["event"] == "ADD"
    with pytest.raises(ValueError):
        m.add(123, user_id="alice")


def test_entity_id_required(m):
    with pytest.raises(MemoryValidationError):
        m.add("x")
    with pytest.raises(ValueError):
        m.add("x", user_id="  ")
    with pytest.raises(ValueError):
        m.search("x")
    with pytest.raises(ValueError):
        m.get_all()
    with pytest.raises(ValueError):
        m.delete_all()


def test_scope_isolation_and_infer_dedup(m):
    a = m.add("Alice likes tennis on weekends", user_id="alice")["results"][0]["id"]
    b = m.add("Alice likes tennis on weekends", user_id="bob")["results"][0]["id"]
    assert a != b                                                 # 不同作用域不合并（核心 M5 去重不看标签）
    assert m.add("Alice likes tennis on weekends", user_id="alice")["results"] == []   # 同作用域 infer=True ⇒ NONE
    again = m.add("Alice likes tennis on weekends", user_id="alice", infer=False)["results"]
    assert len(again) == 1 and again[0]["id"] != a                # infer=False 不去重（同 mem0）
    assert m.add("Alice likes tennis on weekends", user_id="alice", agent_id="x")["results"]   # 作用域不同
    hits = m.search("tennis", filters={"user_id": "bob"})["results"]
    assert [h["id"] for h in hits] == [b]
    assert {h["user_id"] for h in m.get_all(filters={"user_id": "alice"})["results"]} == {"alice"}
    assert m.get_all(filters={"user_id": "alic"})["results"] == []  # 精确标签，不做前缀 / 子串匹配


def test_search_shape_threshold_topk(m):
    for t in ["Paris is the capital of France", "Berlin is the capital of Germany", "I had pasta for lunch"]:
        m.add(t, user_id="u")
    r = m.search("capital of France", filters={"user_id": "u"}, top_k=2)
    res = r["results"]
    assert 1 <= len(res) <= 2 and res[0]["memory"] == "Paris is the capital of France"
    assert all("score" in x for x in res) and [x["score"] for x in res] == sorted((x["score"] for x in res), reverse=True)
    assert m.search("capital of France", filters={"user_id": "u"}, threshold=1.0)["results"] == []
    ex = m.search("pasta", filters={"user_id": "u"}, explain=True)["results"][0]
    assert "score_details" in ex
    with pytest.raises(ValueError):
        m.search("x", filters={"user_id": "u"}, top_k=0)
    with pytest.raises(ValueError):
        m.search("x", filters={"user_id": "u"}, reference_date="2026-01-01")


def test_legacy_top_level_entity_kwargs(m):
    m.add("likes green tea", user_id="v1user")
    assert m.search("green tea", user_id="v1user", limit=1)["results"][0]["memory"] == "likes green tea"
    assert len(m.get_all(user_id="v1user", limit=5)["results"]) == 1


def test_metadata_filters(m):
    m.add("bought a red bike", user_id="u", metadata={"cat": "shopping", "price": 300})
    m.add("bought a blue car", user_id="u", metadata={"cat": "shopping", "price": 30000})
    m.add("went hiking", user_id="u", metadata={"cat": "outdoor"})

    def texts(f):
        return sorted(x["memory"] for x in m.get_all(filters=dict(f, user_id="u"))["results"])

    assert texts({"cat": "shopping"}) == ["bought a blue car", "bought a red bike"]
    assert texts({"price": {"gte": 1000}}) == ["bought a blue car"]
    assert texts({"cat": {"in": ["outdoor"]}}) == ["went hiking"]
    assert texts({"cat": {"ne": "shopping"}}) == ["went hiking"]
    assert texts({"price": "*"}) == ["bought a blue car", "bought a red bike"]
    assert texts({"OR": [{"cat": "outdoor"}, {"price": {"lt": 500}}]}) == ["bought a red bike", "went hiking"]
    assert texts({"NOT": [{"cat": "shopping"}]}) == ["went hiking"]
    hits = m.search("bought", filters={"user_id": "u", "price": {"lt": 500}})["results"]
    assert [h["memory"] for h in hits] == ["bought a red bike"]


def test_identity_keys_in_metadata_are_ignored(m):
    r = m.add("secret plan", user_id="alice", metadata={"user_id": "mallory", "k": 1})["results"][0]
    g = m.get(r["id"])
    assert g["user_id"] == "alice" and g["metadata"] == {"k": 1}
    assert m.get_all(filters={"user_id": "mallory"})["results"] == []


def test_update_delete_history(m):
    mid = m.add("works at Acme", user_id="u")["results"][0]["id"]
    assert m.update(mid, text="works at Globex") == {"message": "Memory updated successfully!"}
    assert m.get(mid)["memory"] == "works at Globex"
    assert m.search("Globex", filters={"user_id": "u"})["results"][0]["id"] == mid    # 改后可按新内容召回
    assert m.search("Acme", filters={"user_id": "u"})["results"] == []
    m.update(mid, metadata={"team": "infra"})
    assert m.get(mid)["metadata"] == {"team": "infra"}
    m.update(mid, data="works at Initech")                          # 旧别名
    assert m.get(mid)["memory"] == "works at Initech"
    with pytest.raises(ValueError):
        m.update(mid)
    with pytest.raises(ValueError):
        m.update("missing", text="x")
    assert m.delete(mid) == {"message": "Memory deleted successfully!"}
    assert m.get(mid) is None
    with pytest.raises(ValueError):
        m.delete(mid)
    h = m.history(mid)
    assert [x["event"] for x in h] == ["ADD", "UPDATE", "UPDATE", "UPDATE", "DELETE"]
    assert set(h[0]) == {"id", "memory_id", "old_memory", "new_memory", "event", "created_at", "updated_at",
                         "is_deleted", "actor_id", "role"}
    assert h[1]["old_memory"] == "works at Acme" and h[1]["new_memory"] == "works at Globex"
    assert h[-1]["is_deleted"] is True and h[-1]["new_memory"] is None


def test_expiration(m):
    m.add("old promo code", user_id="u", expiration_date="2000-01-01")
    m.add("current promo code", user_id="u", expiration_date="2999-01-01")
    assert [x["memory"] for x in m.get_all(filters={"user_id": "u"})["results"]] == ["current promo code"]
    assert len(m.get_all(filters={"user_id": "u"}, show_expired=True)["results"]) == 2
    assert [x["memory"] for x in m.search("promo code", filters={"user_id": "u"})["results"]] == ["current promo code"]


def test_delete_all_and_reset_keep_foreign_nodes(engine):
    m = Memory(engine=engine)
    m.add("a1", user_id="a")
    m.add("b1", user_id="b")
    foreign = engine.perceive("written by someone else").node_id
    assert m.delete_all(user_id="a") == {"message": "Memories deleted successfully!"}
    assert m.get_all(filters={"user_id": "a"})["results"] == []
    assert len(m.get_all(filters={"user_id": "b"})["results"]) == 1
    m.reset()
    assert m.get_all(filters={"user_id": "b"})["results"] == []
    assert engine.store.nodes.get(foreign) is not None              # reset 只动本命名空间
    assert m.get(foreign) is None                                   # 也不把外来节点当成自己的记忆


def test_procedural_memory_not_supported(m):
    with pytest.raises(NotImplementedError):
        m.add("steps", agent_id="a", memory_type="procedural_memory")
    with pytest.raises(ValueError):
        m.add("steps", agent_id="a", memory_type="other")


def test_persistence_across_instances(tmp_path):
    p = str(tmp_path / "mem0.sqlite")
    m1 = Memory(path=p)
    mid = m1.add("persist me", user_id="u")["results"][0]["id"]
    m1.update(mid, text="persisted")
    m1.close()
    m2 = Memory.from_config({"path": p, "llm": {"provider": "openai"}})
    assert m2.get(mid)["memory"] == "persisted"
    assert [x["event"] for x in m2.history(mid)] == ["ADD", "UPDATE"]
    m2.close()


def test_async_memory(engine):
    am = AsyncMemory(engine=engine)

    async def go():
        r = await am.add("async fact about llamas", user_id="u")
        mid = r["results"][0]["id"]
        s = await am.search("llamas", filters={"user_id": "u"})
        await am.update(mid, text="async fact about alpacas")
        g = await am.get(mid)
        allm = await am.get_all(filters={"user_id": "u"})
        h = await am.history(mid)
        await am.delete(mid)
        await am.delete_all(user_id="u")
        await am.reset()
        return s, g, allm, h

    s, g, allm, h = asyncio.run(go())
    assert s["results"][0]["memory"] == "async fact about llamas"
    assert g["memory"] == "async fact about alpacas" and len(allm["results"]) == 1
    assert [x["event"] for x in h] == ["ADD", "UPDATE"]
