# COMPAT_MATRIX · ng 兼容门面 × 上游当前 API

生成：`python tools/compat/compat_matrix.py <上游仓根> --md docs/COMPAT_MATRIX.md`（只读上游 AST，不导入、不执行、不复制实现）。
上游：上游 main ff25e4b。对照面：`lingshu.core.core`（SpacetimeMemoryEngine / LayeredStore / 数据类型 / 模块函数）→ `lingshu_ng.compat`；`lingshu.core.activation.ActivationEngine` → `lingshu_ng.compat_activation`；`lingshu.core.longterm_gate.LongTermMemoryGate` → `lingshu_ng.compat_gate`。

判定：**覆盖**＝同名可调用，且上游每个形参 ng 都接受、上游可省略的 ng 也可省略、ng 多出的形参都有缺省值；**部分**＝同名存在但签名不满足上一条；**缺失**＝无同名对象。**占位**＝签名覆盖、但只由 `compat_stubs` 动态提供：缺省返回上游在器官缺失时的同一缺省值（状态字典或空值，不伪造成功；首次调用打一条 WARNING），`LINGSHU_NG_STRICT_UNSUPPORTED=1` 时调用即抛 `NotSupportedError`（NotImplementedError 子类）；说明列为器官类别与上游缺省返回（`lingshu_ng.compat_stubs.UNSUPPORTED_INFO`，运行期见 `capabilities()["compat_methods"]`）。签名覆盖不等于语义逐项相同；有意不同之处写在各门面方法的 docstring。

| 口径 | 读数 |
|---|---|
| 签名覆盖（含占位） | 246/292（84.2%） |
| 真实覆盖（不含占位） | 201/292（68.8%） |
| 占位 | 45/292（15.4%） |
| 部分 | 15/292（5.1%） |
| 缺失 | 31/292（10.6%） |

频次＝该名字在上游仓（`lingshu/` + `tests/`，排除定义处）以 `.名字(` 被调用的次数。

## 缺失（31）

| 名字 | 上游签名 | 频次 | 说明 |
|---|---|---|---|
| `SpacetimeMemoryEngine.world_process` | `(action, params=…)` | 101 |  |
| `SpacetimeMemoryEngine.add_justification` | `(conclusion_id, premise_ids, source=…)` | 42 |  |
| `SpacetimeMemoryEngine.add_evidence` | `(node_id, source, supports=…, weight=…, note=…, self_generated=…)` | 35 |  |
| `SpacetimeMemoryEngine.evidence_report` | `(node_id)` | 32 |  |
| `SpacetimeMemoryEngine.enable_tms` | `()` | 22 |  |
| `SpacetimeMemoryEngine.enable_evidence_ledger` | `()` | 14 |  |
| `LayeredStore.assert_node_writable_by_role` | `(node_id, action=…)` | 12 |  |
| `LayeredStore.migrate_v17_coordinates` | `()` | 12 |  |
| `LayeredStore.restore_archived` | `(node_id, importance=…)` | 12 |  |
| `LayeredStore.increment_access_many` | `(node_ids, touch=…)` | 11 |  |
| `LayeredStore.layer_writable_by_role` | `(layer)` | 9 |  |
| `LayeredStore.untag_node` | `(node_id, tag)` | 8 |  |
| `LayeredStore.prune_action_logs` | `(keep_rows=…)` | 7 |  |
| `LayeredStore.unverify_edge` | `(edge_id)` | 7 |  |
| `SpacetimeMemoryEngine.prune_action_logs` | `(keep_rows=…)` | 7 |  |
| `LayeredStore.merge_meta` | `(key, value_fn)` | 6 |  |
| `LayeredStore.orphan_protection_rows` | `()` | 4 |  |
| `SpacetimeMemoryEngine.get_current_structure_nodes` | `()` | 4 |  |
| `SpacetimeMemoryEngine.recall_with_evidence` | `(context_content, limit=…, include_refuted=…)` | 4 |  |
| `SpacetimeMemoryEngine.record_structure_event` | `(kind, content, condition_space=…, importance=…, designer_key=…, source=…, metadata=…)` | 4 |  |
| `SpacetimeMemoryEngine.register_world_process` | `(world_process, motion_groups, process_ops=…)` | 4 |  |
| `LayeredStore.close_current_thread` | `()` | 3 |  |
| `LayeredStore.get_escalation_point_by_code` | `(code)` | 3 |  |
| `LayeredStore.list_designer_todos` | `(status=…)` | 3 |  |
| `SpacetimeMemoryEngine.get_escalation_point_by_code` | `(code)` | 3 |  |
| `SpacetimeMemoryEngine.list_designer_todos` | `(status=…)` | 3 |  |
| `SpacetimeMemoryEngine.record_version_event` | `(version, content=…, condition_space=…, designer_key=…, from_version=…, status=…, source=…, metadata=…)` | 2 |  |
| `LayeredStore.add_designer_todo` | `(code, claim, action)` | 1 |  |
| `LayeredStore.assert_nodes_writable_by_role` | `(node_ids, action=…)` | 1 |  |
| `SelfModel.add_value` | `(value, trigger)` | 1 |  |
| `SelfModel.refine_value` | `(old, new, trigger)` | 1 |  |

## 部分（15）

| 名字 | 上游签名 | 频次 | 说明 |
|---|---|---|---|
| `SpacetimeMemoryEngine.add_perception` | `(content, modality=…, spatial_coordinates=…, condition_space=…, importance=…, tags=…, entities=…, skip_dedup=…, source=…, self_generated=…)` | 565 | 缺形参 source；缺形参 self_generated |
| `SpacetimeMemoryEngine.add_edge` | `(source_id, target_id, relation_type=…, confidence=…, condition_space=…, source_evidence=…, dedup=…)` | 171 | 缺形参 dedup |
| `LayeredStore.search_content` | `(query, layers=…, limit=…, touch=…)` | 108 | 缺形参 touch |
| `SpacetimeMemoryEngine.search_content` | `(query, layers=…, limit=…, min_score=…)` | 108 | 缺形参 min_score |
| `SpacetimeMemoryEngine.reason_causal` | `(start_id, end_id=…, max_depth=…, relation_types=…, importance_weighted=…, include_subgraph=…, max_paths=…, causal_stats=…)` | 63 | 缺形参 causal_stats |
| `SpacetimeMemoryEngine.recall` | `(context_content, limit=…, min_score=…)` | 39 | 缺形参 min_score |
| `LayeredStore.adjudicate_verifier_standard` | `(vid, adjudicator, approved, designer_key=…, _cursor=…)` | 16 | 缺形参 _cursor |
| `LayeredStore.add_escalation_point` | `(code, trigger, condition, action, severity=…, designer_key=…)` | 15 | 缺形参 designer_key |
| `SpacetimeMemoryEngine.add_escalation_point` | `(code, trigger, condition, action, severity=…, designer_key=…)` | 15 | 缺形参 designer_key |
| `SpacetimeMemoryEngine.register_external_anchor` | `(kind, content, condition_space=…, designer_key=…, source=…, metadata=…)` | 10 | 缺形参 source；缺形参 metadata |
| `LayeredStore.increment_access` | `(node_id, touch=…)` | 9 | 缺形参 touch |
| `LayeredStore.infer_causal_paths` | `(start_id, end_id, max_depth=…, relation_types=…, max_paths=…, causal_stats=…)` | 8 | 缺形参 causal_stats |
| `LayeredStore.add_promotion_proposal` | `(node_id, requester, reason, override_rejected=…, designer_key=…)` | 5 | 缺形参 override_rejected；缺形参 designer_key |
| `LayeredStore.mark_rejected_path_consumed` | `(rejected_id, designer_key=…)` | 3 | 缺形参 designer_key |
| `SpacetimeMemoryEngine.mark_rejected_path_consumed` | `(rejected_id, designer_key=…)` | 3 | 缺形参 designer_key |

## 占位（签名覆盖，无真实实现）（45）

| 名字 | 上游签名 | 频次 | 说明 |
|---|---|---|---|
| `SpacetimeMemoryEngine.wm_simloop` | `(action, params=…)` | 44 | world_gen（世界推演 / 生成 / 图像语义）；上游缺省 `{status: simloop_not_ready, error}` |
| `SpacetimeMemoryEngine.predict_routes` | `(start_id=…, blindspot_id=…, horizon=…, max_branches=…)` | 13 | prediction（预测 / 语义地图）；上游缺省 `{status: v19_not_ready, error}` |
| `SpacetimeMemoryEngine.annotate_semantics` | `(node_id)` | 9 | semantic_coords（语义坐标列 / 实体注册表）；上游缺省 `False` |
| `SpacetimeMemoryEngine.adjust_attention_weight` | `(key, value, source, reason, role=…)` | 6 | attention（注意力策略的增量接口）；上游缺省 `False` |
| `SpacetimeMemoryEngine.update_prediction_feedback` | `(predicted_node_id, actual_node_id, hit, note=…)` | 5 | prediction（预测 / 语义地图）；上游缺省 `{status: v19_not_ready, error}` |
| `SpacetimeMemoryEngine.pattern_separation_scan` | `(limit=…)` | 4 | scene_memory（模式分离 / 场景重建）；上游缺省 `{created: 0, error}` |
| `SpacetimeMemoryEngine.reconstruct_scene` | `(clue, depth=…, max_nodes=…)` | 3 | scene_memory（模式分离 / 场景重建）；上游缺省 `{scene: [], error}` |
| `SpacetimeMemoryEngine.semantic_neighbors` | `(node_id, k=…)` | 3 | prediction（预测 / 语义地图）；上游缺省 `[]` |
| `SpacetimeMemoryEngine.exploration_budget` | `()` | 2 | self_cognition（自我认知）；上游缺省 `1.0` |
| `SpacetimeMemoryEngine.get_emotional_bias` | `(window=…)` | 2 | self_cognition（自我认知）；上游缺省 `{status: v112_not_ready, error}` |
| `SpacetimeMemoryEngine.world_generator` | `(action, params=…)` | 2 | world_gen（世界推演 / 生成 / 图像语义）；上游缺省 `{status: gen_not_ready, error}` |
| `SpacetimeMemoryEngine.attention_shift` | `(window=…)` | 1 | attention（注意力策略的增量接口）；上游缺省 `0.0` |
| `SpacetimeMemoryEngine.cognition_cycle` | `()` | 1 | self_cognition（自我认知）；上游缺省 `{status: v112_not_ready, error}` |
| `SpacetimeMemoryEngine.cognition_report` | `()` | 1 | self_cognition（自我认知）；上游缺省 `{status: v112_not_ready, error}` |
| `SpacetimeMemoryEngine.confirm_standby` | `(approved)` | 1 | lifecycle（生命周期）；上游缺省 `{status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.enter_standby` | `()` | 1 | lifecycle（生命周期）；上游缺省 `{status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.get_next_candidate` | `()` | 1 | learning_loop（学习闭环）；上游缺省 `None` |
| `SpacetimeMemoryEngine.learn_next` | `(force=…, use_prediction=…)` | 1 | learning_loop（学习闭环）；上游缺省 `{status: v13_not_ready, error}` |
| `SpacetimeMemoryEngine.learning_impact` | `(window=…)` | 1 | self_cognition（自我认知）；上游缺省 `{status: v112_not_ready, error}` |
| `SpacetimeMemoryEngine.mark_contested` | `(node_id, reason)` | 1 | flywheel（进化飞轮）；上游缺省 `False` |
| `SpacetimeMemoryEngine.mark_stale` | `(node_id, reason)` | 1 | flywheel（进化飞轮）；上游缺省 `False` |
| `SpacetimeMemoryEngine.perceive_image` | `(image_path, conf_threshold=…, importance=…, classes=…)` | 1 | vision（视觉闭环）；上游缺省 `{status: vision_unavailable, error}` |
| `SpacetimeMemoryEngine.query_subgraph` | `(query, max_nodes=…)` | 1 | flywheel（进化飞轮）；上游缺省 `{query, nodes: {}, edges: []}` |
| `SpacetimeMemoryEngine.recency_weighted_update` | `(node_id, delta)` | 1 | flywheel（进化飞轮）；上游缺省 `False` |
| `SpacetimeMemoryEngine.render_semantic_cube_3d` | `(entity_id=…, limit=…)` | 1 | prediction（预测 / 语义地图）；上游缺省 `{status: v19_not_ready, error}` |
| `SpacetimeMemoryEngine.render_semantic_map_2d` | `(limit=…)` | 1 | prediction（预测 / 语义地图）；上游缺省 `{status: v19_not_ready, error}` |
| `SpacetimeMemoryEngine.resolve_contested` | `(node_id, verdict)` | 1 | flywheel（进化飞轮）；上游缺省 `False` |
| `SpacetimeMemoryEngine.resolve_crisis` | `(directive, designer_key=…)` | 1 | lifecycle（生命周期）；上游缺省 `设计者密钥无效 → DesignerRequired(PermissionError)；否则 {status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.reverify` | `(node_id)` | 1 | flywheel（进化飞轮）；上游缺省 `False` |
| `SpacetimeMemoryEngine.shortest_path` | `(start_id, end_id, max_depth=…)` | 1 | flywheel（进化飞轮）；上游缺省 `[]` |
| `SpacetimeMemoryEngine.start_lifecycle` | `(interval=…)` | 1 | lifecycle（生命周期）；上游缺省 `{status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.stop_lifecycle` | `(source)` | 1 | lifecycle（生命周期）；上游缺省 `{status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.universe_calibrate` | `()` | 1 | flywheel（进化飞轮）；上游缺省 `{status: v111_not_ready, error}` |
| `SpacetimeMemoryEngine.body_devices` | `()` | 0 | body（身体设备注册表）；上游缺省 `{status: body_not_ready, error, devices: [], health: []}` |
| `SpacetimeMemoryEngine.device_call` | `(name, action, params=…)` | 0 | body（身体设备注册表）；上游缺省 `{status: body_not_ready, error}` |
| `SpacetimeMemoryEngine.evo_distill_cycle` | `(source_filter=…)` | 0 | flywheel（进化飞轮）；上游缺省 `{status: v111_not_ready, error}` |
| `SpacetimeMemoryEngine.evo_flywheel_metrics` | `()` | 0 | flywheel（进化飞轮）；上游缺省 `{status: v111_not_ready, error}` |
| `SpacetimeMemoryEngine.get_prediction_stats` | `()` | 0 | prediction（预测 / 语义地图）；上游缺省 `{status: v19_not_ready, error}` |
| `SpacetimeMemoryEngine.get_self_reliability` | `(window=…)` | 0 | self_cognition（自我认知）；上游缺省 `{status: v112_not_ready, error}` |
| `SpacetimeMemoryEngine.lifecycle_cycle` | `()` | 0 | lifecycle（生命周期）；上游缺省 `{status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.query_by_semantics` | `(text, limit=…, modality=…)` | 0 | semantic_coords（语义坐标列 / 实体注册表）；上游缺省 `[]` |
| `SpacetimeMemoryEngine.run_learning_cycle` | `(input_signal, context=…)` | 0 | learning_loop（学习闭环）；上游缺省 `{status: v13_not_ready, error}` |
| `SpacetimeMemoryEngine.test_transfer_capability` | `()` | 0 | flywheel（进化飞轮）；上游缺省 `{status: v111_not_ready, error}` |
| `SpacetimeMemoryEngine.wake_lifecycle` | `()` | 0 | lifecycle（生命周期）；上游缺省 `{status: v110_not_ready, error}` |
| `SpacetimeMemoryEngine.world_semantics` | `(action, params=…)` | 0 | world_gen（世界推演 / 生成 / 图像语义）；上游缺省 `{status: blindspot, reason, available: []}` |

## 真实覆盖（201）

| 名字 | 上游签名 | 频次 | 说明 |
|---|---|---|---|
| `LayeredStore.close` | `()` | 598 |  |
| `SpacetimeMemoryEngine.close` | `()` | 598 |  |
| `LayeredStore.get_node` | `(node_id)` | 463 |  |
| `LayeredStore.add_edge` | `(edge)` | 171 |  |
| `SelfModel.update` | `(, **kw)` | 153 |  |
| `SpacetimeMemoryEngine.add_context` | `(content, importance=…, condition_space=…, tags=…)` | 132 |  |
| `LayeredStore.add_node` | `(node)` | 130 |  |
| `SpacetimeMemoryEngine.world3d` | `(action, params=…)` | 121 |  |
| `SpacetimeMemoryEngine.import_all` | `(input_path, designer_key=…)` | 101 |  |
| `SpacetimeMemoryEngine.world_model` | `(action, params=…)` | 71 |  |
| `LayeredStore.get_nodes_by_tag` | `(tag, limit=…)` | 70 |  |
| `LayeredStore.decay_cycle` | `(factor=…, min_confidence=…, now=…)` | 69 |  |
| `SpacetimeMemoryEngine.decay_cycle` | `(factor=…, min_confidence=…, now=…)` | 69 |  |
| `SpacetimeMemoryEngine.export_all` | `(output_path)` | 68 |  |
| `ActivationEngine.activate` | `(query, conditions=…, workset=…, top_k=…, hops=…, act_floor=…, self_condition=…, prior_workset=…)` | 64 |  |
| `LayeredStore.delete_node` | `(node_id)` | 60 |  |
| `LayeredStore.get_meta` | `(key=…)` | 57 |  |
| `LayeredStore.query_nodes` | `(layer=…, modality=…, min_importance=…, limit=…)` | 55 |  |
| `LayeredStore.get_edge` | `(edge_id)` | 52 |  |
| `SelfModel.to_dict` | `()` | 52 |  |
| `LongTermMemoryGate.evaluate` | `(content, source=…, tags=…, existing_id=…, novelty=…)` | 50 |  |
| `LayeredStore.tag_node` | `(node_id, tag)` | 49 |  |
| `SpacetimeMemoryEngine.seven_layer_loop` | `(action, params=…)` | 45 |  |
| `SpacetimeMemoryEngine.update_self` | `(updates, link_to_node_id=…)` | 45 |  |
| `LayeredStore.protect_node` | `(node_id, reason)` | 42 |  |
| `SpacetimeMemoryEngine.protect_node` | `(node_id, reason)` | 42 |  |
| `LayeredStore.insight_record` | `(content, conditions=…, source=…, importance=…)` | 40 |  |
| `LayeredStore.insight_verify` | `(insight_id, level=…, evidence=…)` | 40 |  |
| `SpacetimeMemoryEngine.set_context_cap` | `(max_size)` | 39 |  |
| `LayeredStore.count_layer` | `(layer)` | 37 |  |
| `SpacetimeMemoryEngine.check_escalation` | `(signal_type, value=…)` | 35 |  |
| `SpacetimeMemoryEngine.longterm_snapshot` | `(content, source=…, tags=…, entities=…, importance_hint=…)` | 35 |  |
| `LayeredStore.verify_edge` | `(edge_id, new_confidence=…)` | 34 |  |
| `SpacetimeMemoryEngine.apply_shared_sync` | `(payload, overwrite=…)` | 34 |  |
| `SpacetimeMemoryEngine.verify_edge` | `(edge_id, new_confidence=…)` | 34 |  |
| `ActivationEngine.carry_vector` | `(workset=…)` | 33 |  |
| `LayeredStore.get_protected_nodes` | `()` | 33 |  |
| `SpacetimeMemoryEngine.get_protected_nodes` | `()` | 33 |  |
| `ConditionSpace.to_json` | `()` | 31 |  |
| `SpacetimeMemoryEngine.set_anchor` | `(content, importance=…, condition_space=…)` | 30 |  |
| `SpacetimeMemoryEngine.world_learner` | `(action, params=…)` | 28 |  |
| `SelfModel.update_trust_state` | `(t_total, round_no, p_trust=…, p_gap=…)` | 27 |  |
| `SpacetimeMemoryEngine.update_trust_state` | `(t_total, round_no, p_trust=…, p_gap=…)` | 27 |  |
| `LayeredStore.get_skill_by_name` | `(name)` | 25 |  |
| `SpacetimeMemoryEngine.visual_check` | `(reference=…, threshold=…, remember=…)` | 25 |  |
| `LayeredStore.char_bigram_jaccard` | `(a, b)` | 23 |  |
| `SelfModel.record_value_change` | `(value, trigger)` | 23 |  |
| `SpacetimeMemoryEngine.add_structure_node` | `(content, importance=…, condition_space=…)` | 23 |  |
| `SpacetimeMemoryEngine.self_check` | `()` | 23 |  |
| `LayeredStore.adjudicate_promotion` | `(proposal_id, adjudicated_by, approved, designer_key=…)` | 22 |  |
| `LayeredStore.log_action` | `(action_type, summary=…, node_ids=…, outcome=…, context=…)` | 22 |  |
| `LayeredStore.register_conflict` | `(a_id, b_id, condition_space=…)` | 22 |  |
| `SpacetimeMemoryEngine.adjudicate_promotion` | `(proposal_id, adjudicated_by, approved, designer_key=…)` | 22 |  |
| `SpacetimeMemoryEngine.register_conflict` | `(a_id, b_id)` | 22 |  |
| `LayeredStore.get_outgoing_edges` | `(node_id)` | 21 |  |
| `LayeredStore.recalc_structural_importance` | `(dry_run=…, boost_cap=…, beta=…, gamma=…, c=…, min_degree=…, min_causal=…, min_delta=…, max_depth=…, protect_threshold=…, floor_importance=…)` | 21 |  |
| `SpacetimeMemoryEngine.subgraph_replace` | `(parent_id, old_sub_root_id, new_subtree)` | 21 |  |
| `ActivationEngine.workset_state` | `(workset=…, limit=…)` | 20 |  |
| `LayeredStore.list_escalation_points` | `(enabled_only=…)` | 20 |  |
| `LayeredStore.set_meta` | `(key, value)` | 20 |  |
| `SpacetimeMemoryEngine.list_escalation_points` | `(enabled_only=…)` | 20 |  |
| `SpacetimeMemoryEngine.propose_promotion` | `(node_id, requester, reason, override_rejected=…, designer_key=…)` | 20 |  |
| `SpacetimeMemoryEngine.start_auto_decay` | `(interval=…, clock=…)` | 20 |  |
| `ConditionSpace.from_json` | `(s)` | 19 |  |
| `SpacetimeMemoryEngine.prepare_shared_sync` | `()` | 18 |  |
| `ActivationEngine.export_workset` | `(workset)` | 17 |  |
| `LayeredStore.add_blindspot` | `(code, description, severity=…, category=…, predictability=…)` | 17 |  |
| `LayeredStore.get_stats` | `()` | 17 |  |
| `SpacetimeMemoryEngine.forget_advisor` | `(stale_days=…, low_value=…, archived_imp=…)` | 17 |  |
| `SpacetimeMemoryEngine.get_stats` | `()` | 17 |  |
| `SpacetimeMemoryEngine.get_verifier_config` | `()` | 17 |  |
| `SpacetimeMemoryEngine.spacetime_consistency` | `(action, params=…)` | 17 |  |
| `LayeredStore.find_cycles` | `(max_depth=…, limit=…)` | 16 |  |
| `LayeredStore.spatiotemporal_query` | `(center_node_id, time_radius=…, space_metric=…, space_radius=…, max_results=…)` | 16 |  |
| `SpacetimeMemoryEngine.adjudicate_verifier_standard` | `(vid, adjudicator, approved, designer_key=…)` | 16 |  |
| `SpacetimeMemoryEngine.recursive_reflect` | `(claim, expected=…, actual=…, context=…, depth=…, max_depth=…)` | 16 |  |
| `SpacetimeMemoryEngine.spatiotemporal_query` | `(node_id, time_radius=…, space_metric=…, space_radius=…, max_results=…)` | 16 |  |
| `SpacetimeMemoryEngine.store_skill` | `(name, description, procedure, confidence=…)` | 16 |  |
| `LayeredStore.update_node_importance` | `(node_id, delta)` | 15 |  |
| `LayeredStore.verify_promotion` | `(proposal_id, verified_by)` | 15 |  |
| `SpacetimeMemoryEngine.record_action_sequence` | `(actions, outcome, success, skill_hint=…)` | 15 |  |
| `SpacetimeMemoryEngine.verify_promotion` | `(proposal_id, verified_by)` | 15 |  |
| `cond_match` | `(cs_a, cs_b)` | 15 |  |
| `ActivationEngine.import_workset` | `(snapshot, workset=…)` | 14 |  |
| `LongTermMemoryGate.write_snapshot` | `(content, source=…, tags=…, entities=…, importance_hint=…)` | 14 |  |
| `SpacetimeMemoryEngine.stop_auto_decay` | `()` | 14 |  |
| `LayeredStore.list_blindspots` | `(status=…)` | 13 |  |
| `LayeredStore.prune_self_snapshots` | `(keep)` | 13 |  |
| `LayeredStore.search_skills` | `(query, limit=…)` | 13 |  |
| `LayeredStore.traverse` | `(start_id, relation_types=…, direction=…, max_depth=…, min_importance=…, max_nodes=…)` | 13 |  |
| `LayeredStore.update_node_confidence` | `(node_id, delta)` | 13 |  |
| `SpacetimeMemoryEngine.curiosity_explorer` | `(action, params=…)` | 13 |  |
| `SpacetimeMemoryEngine.export_trajectory` | `(cycle_id=…, output_path=…, _limit=…)` | 13 |  |
| `SpacetimeMemoryEngine.list_blindspots` | `(status=…)` | 13 |  |
| `SpacetimeMemoryEngine.prune_self_snapshots` | `(keep=…)` | 13 |  |
| `SpacetimeMemoryEngine.traverse` | `(start_id, relation_types=…, direction=…, max_depth=…, min_importance=…, max_nodes=…)` | 13 |  |
| `LayeredStore.cs_review_verifier_standard` | `(vid, reviewer, approved)` | 12 |  |
| `LayeredStore.get_layer_nodes` | `(layer)` | 12 |  |
| `LayeredStore.review_verifier_standard` | `(vid, reviewer, approved)` | 12 |  |
| `SpacetimeMemoryEngine.cs_review_verifier_standard` | `(vid, reviewer, approved)` | 12 |  |
| `SpacetimeMemoryEngine.migrate_v17_coordinates` | `()` | 12 |  |
| `SpacetimeMemoryEngine.record_info_gap` | `(d_norm=…, trust_complement=…, behavior_deviation=…, connection_drift=…, prediction_error=…)` | 12 |  |
| `SpacetimeMemoryEngine.review_verifier_standard` | `(vid, reviewer, approved)` | 12 |  |
| `LayeredStore.expand_query_terms` | `(query)` | 11 |  |
| `LayeredStore.get_incoming_edges` | `(node_id)` | 11 |  |
| `LayeredStore.set_escalation_enabled` | `(escalation_id, enabled, designer_key=…)` | 11 |  |
| `SpacetimeMemoryEngine.scene_simulator` | `(action, params=…)` | 11 |  |
| `SpacetimeMemoryEngine.set_escalation_enabled` | `(escalation_id, enabled, designer_key=…)` | 11 |  |
| `SpacetimeMemoryEngine.verify_integrity` | `()` | 11 |  |
| `LayeredStore.enforce_context_cap` | `(max_size)` | 10 |  |
| `LayeredStore.get_nodes_in_range` | `(start_ts, end_ts, layer=…, limit=…)` | 10 |  |
| `SpacetimeMemoryEngine.get_gap_trend` | `(window=…)` | 10 |  |
| `SpacetimeMemoryEngine.run_maintenance_cycle` | `(decay_factor=…)` | 10 |  |
| `LayeredStore.add_verifier_standard` | `(name, param, value, reason, proposer)` | 9 |  |
| `LayeredStore.query_nodes_by_time` | `(start_ts=…, end_ts=…, limit=…)` | 9 |  |
| `SelfModel.from_dict` | `(data)` | 9 |  |
| `SpacetimeMemoryEngine.register_blindspot` | `(code, description, severity=…, category=…, predictability=…)` | 9 |  |
| `ActivationEngine.__init__` | `(db_path=…, audit_path=…, conn=…, store=…)` | 8 |  |
| `CausalChain.__init__` | `(edges=…, truncated=…, cyclic=…)` | 8 |  |
| `LayeredStore.__init__` | `(db_path=…, role=…)` | 8 |  |
| `LongTermMemoryGate.__init__` | `(engine, weights=…)` | 8 |  |
| `SpacetimeMemoryEngine.__init__` | `(db_path=…, identity=…, role=…)` | 8 |  |
| `SpacetimeMemoryEngine.consolidate_cycle` | `(rehearsal_threshold=…, degrade_threshold=…, gain=…)` | 8 |  |
| `verify_designer` | `(designer_key)` | 8 |  |
| `LayeredStore.add_skill` | `(name, description, procedure, confidence=…)` | 7 |  |
| `LayeredStore.get_recent_context` | `(limit=…)` | 7 |  |
| `LayeredStore.update_blindspot_status` | `(blindspot_id, status, designer_key=…)` | 7 |  |
| `SpacetimeMemoryEngine.export_structured_trajectories` | `(limit=…, output_path=…)` | 7 |  |
| `SpacetimeMemoryEngine.get_recent_context` | `(limit=…)` | 7 |  |
| `SpacetimeMemoryEngine.ingest_frame` | `(frame_data, entity_hint=…, state_hint=…, semantic_attention=…, condition_space=…)` | 7 |  |
| `SpacetimeMemoryEngine.set_semantic_provider` | `(provider)` | 7 |  |
| `LayeredStore.add_rejected_path` | `(path_type, description, reason, evidence=…)` | 6 |  |
| `LayeredStore.list_rejected_paths` | `(status=…)` | 6 |  |
| `LayeredStore.resolve_blindspot` | `(blindspot_id, designer_key=…)` | 6 |  |
| `STEdge.from_row` | `(row)` | 6 |  |
| `STNode.from_row` | `(row)` | 6 |  |
| `SpacetimeMemoryEngine.consume_events` | `()` | 6 |  |
| `SpacetimeMemoryEngine.find_rejected_paths` | `(query, limit=…)` | 6 |  |
| `SpacetimeMemoryEngine.list_rejected_paths` | `(status=…)` | 6 |  |
| `SpacetimeMemoryEngine.prefeed_input` | `(content, source=…, tags=…, entities=…)` | 6 |  |
| `SpacetimeMemoryEngine.recall_skill` | `(query, limit=…)` | 6 |  |
| `SpacetimeMemoryEngine.resolve_blindspot` | `(blindspot_id, resolved=…, note=…, designer_key=…)` | 6 |  |
| `SpacetimeMemoryEngine.set_dedup_config` | `(static_threshold=…, window=…)` | 6 |  |
| `LayeredStore.subgraph` | `(root_id, max_depth=…, relation_types=…, direction=…)` | 5 |  |
| `LayeredStore.update_skill_confidence` | `(skill_id, delta)` | 5 |  |
| `LongTermMemoryGate.prefeed` | `(content, source=…, tags=…, entities=…)` | 5 |  |
| `SpacetimeMemoryEngine.subgraph` | `(root_id, max_depth=…, relation_types=…)` | 5 |  |
| `SpacetimeMemoryEngine.timeline` | `(node_id, direction=…, max_depth=…)` | 5 |  |
| `SpacetimeMemoryEngine.update_skill_confidence` | `(skill_id, delta)` | 5 |  |
| `SpacetimeMemoryEngine.voxel_world` | `(action, params=…)` | 5 |  |
| `LayeredStore.insight_report` | `(window=…)` | 4 |  |
| `LayeredStore.insight_window` | `(conditions=…)` | 4 |  |
| `SpacetimeMemoryEngine.get_body_capabilities` | `()` | 4 |  |
| `SpacetimeMemoryEngine.induce_concepts` | `(min_cluster_size=…, similarity_threshold=…, max_concepts=…, condition_space=…)` | 4 |  |
| `SpacetimeMemoryEngine.promote_context_memories` | `(limit=…)` | 4 |  |
| `SpacetimeMemoryEngine.session_summary` | `(window_seconds=…, limit=…)` | 4 |  |
| `LayeredStore.has_causal_cycle` | `()` | 3 |  |
| `STEdge.to_row` | `()` | 3 |  |
| `STNode.to_row` | `()` | 3 |  |
| `SpacetimeMemoryEngine.register_rejected_path` | `(path_type, description, reason, evidence=…)` | 3 |  |
| `LayeredStore.list_verifier_standards` | `(status=…)` | 2 |  |
| `LongTermMemoryGate.promote_from_context` | `(limit=…)` | 2 |  |
| `SpacetimeMemoryEngine.consolidate_learning_result` | `(record)` | 2 |  |
| `SpacetimeMemoryEngine.get_anchors` | `()` | 2 |  |
| `SpacetimeMemoryEngine.get_open_blindspots` | `()` | 2 |  |
| `SpacetimeMemoryEngine.get_self_model` | `()` | 2 |  |
| `SpacetimeMemoryEngine.list_verifier_standards` | `(status=…)` | 2 |  |
| `SpacetimeMemoryEngine.notify_event` | `(event_type, payload=…)` | 2 |  |
| `SpacetimeMemoryEngine.propose_verifier_standard` | `(name, param, value, reason, proposer)` | 2 |  |
| `LayeredStore.append_skill_procedure` | `(skill_id, step)` | 1 |  |
| `LayeredStore.count_skills` | `()` | 1 |  |
| `LayeredStore.semantic_search` | `(query, provider, limit=…)` | 1 |  |
| `SelfModel.retire_value` | `(value, trigger)` | 1 |  |
| `SpacetimeMemoryEngine.action_log_stats` | `()` | 1 |  |
| `SpacetimeMemoryEngine.allocate_depth` | `(signal, context=…)` | 1 |  |
| `SpacetimeMemoryEngine.apply_value_candidate` | `(candidate_id, new_value=…)` | 1 |  |
| `SpacetimeMemoryEngine.filter_attention` | `(signals, threshold=…)` | 1 |  |
| `SpacetimeMemoryEngine.get_action_log` | `(limit=…)` | 1 |  |
| `SpacetimeMemoryEngine.get_entity_context` | `(entity_id, limit=…)` | 1 |  |
| `SpacetimeMemoryEngine.resolve_concepts` | `(text)` | 1 |  |
| `SpacetimeMemoryEngine.semantic_search` | `(query, limit=…)` | 1 |  |
| `SpacetimeMemoryEngine.what_happened_at` | `(timestamp, tolerance=…, limit=…)` | 1 |  |
| `LayeredStore.conn` | `()` | 0 |  |
| `SpacetimeMemoryEngine.attend_query` | `(query, limit=…, source=…)` | 0 |  |
| `SpacetimeMemoryEngine.check_recursion_depth` | `(depth)` | 0 |  |
| `SpacetimeMemoryEngine.compiler_introspect` | `()` | 0 |  |
| `SpacetimeMemoryEngine.compute_semantic_coordinates` | `(text)` | 0 |  |
| `SpacetimeMemoryEngine.get_attention_policy` | `()` | 0 |  |
| `SpacetimeMemoryEngine.get_resource_metrics` | `(window=…)` | 0 |  |
| `SpacetimeMemoryEngine.get_semantic_provider` | `()` | 0 |  |
| `SpacetimeMemoryEngine.get_timeline` | `(start_ts=…, end_ts=…, layer=…, limit=…)` | 0 |  |
| `SpacetimeMemoryEngine.get_vision_provider` | `()` | 0 |  |
| `SpacetimeMemoryEngine.record_resource_usage` | `(tokens=…, seconds=…)` | 0 |  |
| `SpacetimeMemoryEngine.semantic_blindspot_report` | `()` | 0 |  |
| `SpacetimeMemoryEngine.set_attention_policy` | `(policy)` | 0 |  |
| `SpacetimeMemoryEngine.set_embedding_provider` | `(provider)` | 0 |  |
| `SpacetimeMemoryEngine.set_vision_provider` | `(provider)` | 0 |  |
| `SpacetimeMemoryEngine.sync_body_state` | `()` | 0 |  |
| `SpacetimeMemoryEngine.voice_session_log` | `(turn)` | 0 |  |
| `SpacetimeMemoryEngine.vprim_query` | `(action, params=…)` | 0 |  |
| `designer_key_configured` | `()` | 0 |  |

## 扩展面（stab-r2 起计量，单独汇总）

上游 `lingshu.core` 其余公开模块：`lingshu/core/provenance.py`、`lingshu/core/time_core.py`、`lingshu/core/condition_normalize.py`、`lingshu/core/verdict.py`、`lingshu/core/component_resolver.py`。ng 未提供同名模块，按 `lingshu_ng.compat` 查同名对象。这些是上游较新的内部工具面（来源记录、可信度时间核、条件规范化、部件判定、组件发现），ng 目前没有对应实现，照实列为缺失。

| 口径 | 读数 |
|---|---|
| 签名覆盖（含占位） | 0/29 |
| 真实覆盖 | 0/29 |
| 部分 | 1/29 |
| 缺失 | 28/29 |

| 名字 | 上游位置 | 上游签名 | 频次 | 状态 |
|---|---|---|---|---|
| `install` | `lingshu/core/component_resolver.py` | `()` | 11 | 缺失 |
| `safe_search_path` | `lingshu/core/component_resolver.py` | `()` | 9 | 缺失 |
| `is_installed` | `lingshu/core/component_resolver.py` | `()` | 4 | 缺失 |
| `configured_roots` | `lingshu/core/component_resolver.py` | `()` | 1 | 缺失 |
| `discovery_report` | `lingshu/core/component_resolver.py` | `()` | 1 | 缺失 |
| `validate_edges` | `lingshu/core/condition_normalize.py` | `(domains)` | 10 | 缺失 |
| `canonical_condition` | `lingshu/core/condition_normalize.py` | `(domains)` | 6 | 缺失 |
| `cond_hash` | `lingshu/core/condition_normalize.py` | `(domains, salt=…)` | 2 | 缺失 |
| `canonical_sourced` | `lingshu/core/condition_normalize.py` | `(domains, asserted_by=…)` | 1 | 缺失 |
| `invalid_domains` | `lingshu/core/condition_normalize.py` | `(domains)` | 1 | 缺失 |
| `img0_domains` | `lingshu/core/condition_normalize.py` | `()` | 0 | 缺失 |
| `part_cond_hash` | `lingshu/core/condition_normalize.py` | `(part_type, image_hash, part_idx)` | 0 | 缺失 |
| `Provenance.to_json` | `lingshu/core/provenance.py` | `()` | 31 | 缺失 |
| `Provenance.strength` | `lingshu/core/provenance.py` | `()` | 26 | 缺失 |
| `Provenance.from_json` | `lingshu/core/provenance.py` | `(s)` | 19 | 缺失 |
| `Provenance.to_condition_space` | `lingshu/core/provenance.py` | `()` | 6 | 缺失 |
| `Provenance.to_tags` | `lingshu/core/provenance.py` | `(extra=…)` | 6 | 缺失 |
| `Provenance.is_traceable` | `lingshu/core/provenance.py` | `()` | 5 | 缺失 |
| `Provenance.validate` | `lingshu/core/provenance.py` | `()` | 5 | 缺失 |
| `Provenance.to_sql` | `lingshu/core/provenance.py` | `(extra_tags=…)` | 4 | 缺失 |
| `Provenance.extensions` | `lingshu/core/provenance.py` | `()` | 0 | 缺失 |
| `from_legacy` | `lingshu/core/provenance.py` | `(tags, created_at=…, condition_space=…, modality=…)` | 0 | 缺失 |
| `is_default_cs` | `lingshu/core/provenance.py` | `(cs)` | 0 | 缺失 |
| `new_provenance` | `lingshu/core/provenance.py` | `(position, tool, source, session_id=…, existence_constraint=…, verify_status=…, verify_methods=…, verify_ref=…, observed_at=…, window=…)` | 0 | 缺失 |
| `cred_step` | `lingshu/core/time_core.py` | `(x, decay)` | 11 | 部分 |
| `cred_factor` | `lingshu/core/time_core.py` | `(gamma, dt, floor=…, ceil=…)` | 9 | 缺失 |
| `cred_blend` | `lingshu/core/time_core.py` | `(last, incoming, retain)` | 4 | 缺失 |
| `cred` | `lingshu/core/time_core.py` | `(x0, x_inf, gamma, dt)` | 2 | 缺失 |
| `assess` | `lingshu/core/verdict.py` | `(part, image_domains, part_fg_px, part_area)` | 19 | 缺失 |
