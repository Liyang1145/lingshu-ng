# -*- coding: utf-8 -*-
"""induce_concepts：新成员并入既有概念，不另起重复概念（对照上游 d08ae59）"""
from lingshu_ng.compat import SpacetimeMemoryEngine


def _concepts(c):
    return [n for n in c.ng.store.nodes.scan() if "induced" in n.tags and "concept" in n.tags]


def test_new_member_merges_into_existing_concept():
    c = SpacetimeMemoryEngine(":memory:")
    base = "用户每天早上喝咖啡并且阅读新闻"
    for i in range(3):
        c.add_perception(base + "甲乙丙"[i], skip_dedup=True)
    assert len(c.induce_concepts(min_cluster_size=3, similarity_threshold=0.5)) == 1
    for i in range(2):
        c.add_perception(base + "丁戊"[i], skip_dedup=True)
    c.induce_concepts(min_cluster_size=3, similarity_threshold=0.5)
    cs = _concepts(c)
    assert len(cs) == 1
    members = [e.target_id for e in c.store.get_outgoing_edges(cs[0].id)]
    assert len(members) == 5
