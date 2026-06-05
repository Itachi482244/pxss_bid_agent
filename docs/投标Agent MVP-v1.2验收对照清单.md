# 投标 Agent MVP-v1.2 验收标准逐条对照清单

> 生成时间：2026-06-04
> 对照对象：《投标Agent MVP-v1.2需求规划与开发进度》第 10 节验收标准 #1–#10
> 结论口径：达成 / 部分达成 / 未达成，均给出代码、接口或测试证据，未达成项标注缺口与后续动作。

## 总览

| # | 验收标准 | 结论 | 主要证据 |
| --- | --- | --- | --- |
| 1 | 生成前可看完整 ContextPack 预览 | 达成 | `context-pack/preview` 接口 + happy-path 回归 |
| 2 | ContextPack 显示来源/版本/矩阵/证据/风险/缺项 | 达成 | `build_context_pack_preview` context_json 字段 |
| 3 | 无证据事实不被编造成确定性陈述 | 达成 | `_section_context_from_outline` 缺项占位 + `needs_evidence` block |
| 4 | 每个 block 回链合规条目和证据 | 达成 | `DraftBlock.links_json` + blocks 回归断言 |
| 5 | 强制/高风险/资格项未处理不静默进入生成稿 | 达成 | readiness block 门禁 + 异常路径回归 |
| 6 | 生成后校验发现项目名/日期/证书/人员/业绩异常 | 部分达成 | `run_fact_checks` + CoverageReview；人员/业绩细分规则待增强 |
| 7 | 审阅视图支持正文↔合规条目双向定位 | 达成（首版） | block 审阅 + `links_json` 双向链 |
| 8 | 审阅/修改/风险接受/导出均写审计 | 达成 | 各动作 `AuditLog` 落库 |
| 9 | Word 导出只基于审阅通过的结构化稿 | 达成 | `draft_block_review` 提交前门禁 + 导出回归 |
| 10 | 回归覆盖正常/缺证据/字段缺失/版本过期/模型失败 | 部分达成 | 已覆盖正常/缺证据/字段缺失/生成失败；版本过期仅软提示，缺硬门禁与专测 |

## 逐条说明

### #1 生成前可看完整 ContextPack 预览 — 达成
- 接口：`POST /projects/{pid}/sections/{sid}/business-draft/context-pack/preview`。
- 实现：`context_pack.build_context_pack_preview`，返回 `profile_id`、`schema_version`、`readiness_status`、`context_json`、`outline_plan_json`。
- 测试：`test_mvp12_context_pack_api.py` 断言预览结构、矩阵汇总、章节范围。

### #2 来源/版本/矩阵/证据/风险/缺项可见 — 达成
- `context_json` 含 `project_facts`、`source_document`（含 `current_version_id`）、`matrix_items`、`bound_evidence`、`missing_facts`、`qualification_decision`、`readiness_json.checks`。
- 风险与缺项以 readiness check 形式输出（`matrix.*`、`evidence.*`、`project_fields.missing`、`qualification.*`）。

### #3 无证据事实不被编造 — 达成
- `_section_context_from_outline` 对「需要企业证据但未绑定」的条目写入 `missing_facts` 占位；对缺失必填字段写入待补占位。
- `_build_section_draft_content` / `_add_draft_blocks` 用占位文案而非编造，block `review_status` 标记 `needs_evidence` / `needs_fact`。

### #4 block 回链合规条目和证据 — 达成
- `DraftBlock.links_json` 记录 `context_pack_id`、`compliance_item_ids`、`evidence_binding_ids`。
- 测试：happy-path 断言 `block["links_json"]["context_pack_id"]`；前端支持 block↔矩阵↔原文跳转。

### #5 强制/高风险/资格项未处理不静默进入 — 达成
- `_readiness_checks` 对未确认的高风险/强制/资格项产出 `matrix.guard_items_unconfirmed`（block），对缺证据产出 `evidence.missing_required`（block）。
- `generate_draft_from_context_pack` 在 `readiness_status == "block"` 且未显式允许内部草稿时拒绝生成。
- 测试（新增）：`test_mvp12_context_pack_exceptions.py::test_readiness_flags_missing_evidence_and_unconfirmed_guard_items` 与 `test_async_generate_blocks_then_allows_internal_draft`。

### #6 生成后事实校验 — 部分达成
- 已有：`business_draft.run_fact_checks` 校验项目名、日期、证书编号等硬字段；`create_coverage_review` 输出覆盖率、证据引用率、待补/缺证计数、`quality_score`。
- 缺口：人员资格、业绩匹配等细分事实规则尚未单独成项（规划文档第 7 节 P0「生成后校验」已注明「人员/业绩等细分规则待增强」）。
- 后续动作：在 fact-check 中增加人员证书有效期、业绩金额/时间窗匹配规则及对应回归。

### #7 正文↔合规条目双向定位 — 达成（首版）
- 后端 `DraftBlock.links_json` 提供双向锚点；前端商务标章节页支持矩阵条款跳回覆盖它的 block，block 跳转矩阵/原文抽屉/矩阵审阅台。

### #8 审阅/修改/风险接受/导出写审计 — 达成
- block 审阅与内容修改、`context_pack_generated`、导出门禁与风险接受、异步生成任务的 `requested/succeeded/failed` 均写 `AuditLog`。

### #9 Word 导出只基于审阅通过稿 — 达成
- 提交前核验 `draft_block_review`：存在未审阅通过的 MVP1.2 block 时导出返回 409；全部 `approved` 后方可导出，导出快照记录 `unresolved == 0`。
- 测试：happy-path 先 409 后 200，并校验 `source_snapshot_json.draft_block_review.unresolved`。

### #10 固定样本回归覆盖五类场景 — 部分达成
| 场景 | 覆盖 | 证据 |
| --- | --- | --- |
| 正常生成 | 已覆盖 | `test_mvp12_context_pack_api` 全链路 |
| 缺证据 | 已覆盖 | `test_mvp12_context_pack_exceptions`（`evidence.missing_required` + block→内部草稿） |
| 字段缺失 | 已覆盖 | `test_mingzhu_mock_enterprise_data`（`project_fields.missing` / missing_facts）、readiness warn |
| 模型/生成失败 | 已覆盖 | 异步任务失败路径 `BUSINESS_DRAFT_GENERATION_BLOCKED`，不保存有效草稿 |
| 版本过期 | 部分 | 仅 `source_document.missing_current_version`（warn 软提示），无「版本过期硬门禁」与专测 |

- 缺口：规划文档第 8 节将「文档版本过期」列为「默认不允许」，但当前 readiness 仅在缺当前版本快照时给 warn，未实现「矩阵基于的版本已被新版本取代」的硬阻塞。
- 后续动作：在 readiness 增加「矩阵 source_version 落后于文档 current_version」检测（block/warn），并补一条版本过期回归。

## 本版本新增的异步生成能力（对应规划第 9 节 `draft_generation_tasks`）

> 规划第 9 节原列 `draft_generation_tasks`「暂未新增，当前生成仍是同步接口」。本次已落地异步通道，未单独建表，而是复用 `async_tasks` + 通用 `/tasks/{id}` 轮询，降低改造面与回归风险。

- 模型：`AsyncTask.task_type` 新增 `business_draft_generate`（迁移 `a3c9e7d2b5f1`）。
- 服务：`context_pack.execute_business_draft_generation_task` 驱动 running→succeeded/failed，`output_json` 记录章节/ block / 覆盖结论，失败不保存有效草稿。
- Worker：`tasks.business_draft_generate`。
- 接口：`POST .../context-pack/{cid}/generate-async`（202，返回 `AsyncTaskRead`），复用 `run_tasks_inline` 与 `enqueue_celery_task`；broker 不可用时 503。
- 同步接口 `.../generate` 保留，小文档可继续同步直返结果。
- 测试：`test_mvp12_context_pack_exceptions.py` 覆盖异步成功/失败状态机、block→内部草稿、No-Go 仅内部草稿。

## 验收结论

- 10 条标准中 8 条达成、2 条部分达成（#6 生成后人员/业绩细分校验、#10 版本过期硬门禁）。
- 部分达成项均为「增强/硬化」而非核心缺失，已在上文标注后续动作。
- 全量后端测试：133 passed；迁移链单头部 `a3c9e7d2b5f1`。
