# 投标 Agent MVP-v1.6 半自主编排设计（推进助手）

> 更新时间：2026-06-14
> 状态：评审修订稿（P0 边界已补齐，待拆开发任务）
> 前置：建议先完成 MVP1.5.5（易用性与标书质量打磨），把质量体检、导出前确认、待办减负、候选证据解释和样张/浏览器验收等人工链路收口稳定后再启动本版——本版只负责自动触发与串联，不重新发明用户要理解的概念。详见 `docs/投标Agent MVP-v1.5.5易用性与标书质量打磨方案.md`。
> 目标：把当前「RAG 增强的投标副驾」升级为**半自主**——Agent 替你把多步无聊活串起来做好，但**用起来要极简**：一个按钮、就地确认、一个待办队列。
> 不做：全自主（自动绑证据/自动改写、人只事后审批）；也不做让用户去管理「运行 / 提案」的复杂控制台。

## 0. 设计第一原则：用起来简单

把「半自主」做成用户能感知的**最少东西**。四条标准，后面所有取舍照它来：

1. **入口要少**——不该有「先建 run → 再看 proposal → 再去绑定」的三跳，最好就一个按钮。
2. **不造新名词**——用户脑子里只有他已经懂的词：**合规项、证据、草稿、待办**。`agent run` / `proposal` / `tool` 是后台管道，**永不进用户视野**。
3. **在他已经在的地方做决定**——建议就地长在他本来就在看的界面里（合规矩阵那一行冒出「建议绑这条 + 理由」，点一下采纳），不要把他支到另一个「提案页」。
4. **安全默认 + 渐进展开**——默认一键跑、就地确认；想看「Agent 怎么得出的」的人才点开细节。

> 上一版设计（独立提案收件箱、agent-runs 管理、GATE-1/GATE-2 两个新面板）工程上整洁，但给用户增加了页面和概念，违背本原则，已废弃。

## 1. 背景与定位

当前 `backend/app/agents/`、`tools/`、`harness/` 是空壳。仓库内没有 tool-calling、多步循环、planning。LLM 能力分散在 13 个 service 里，以「单次结构化调用」被 API 直接触发，交互是「人点一下 → 跑一个 service → 再点一下」。

本设计加一层**编排管道**把这串连起来自动跑，但**对用户只暴露一个「推进」按钮 + 就地建议 + 一个待办队列**。产品原则不变：模型只在已确认上下文之上生成；不绕开上下文；责任落在人头上。

## 2. 用户看到的全部（就这些）

```
当前标段工作区一个按钮：   ▶ 让 Agent 帮我推进
        │（后台默默跑：找证据 → 排序 → 产理由 → 产草稿 → 自检，全是管道）
        ▼
回到你本来就用的界面，只多两样东西：
  · 合规矩阵行内：  💡 建议绑定「营业执照（2024版）」  [采纳] [换一条] [忽略]
  · 顶部一个「待办」红点： 还有 8 项要你拍板（缺证据 3 / 草稿待审 4 / 无支撑 1）→ 点开就是现有审阅界面
```

用户要学的概念为零：他只是看到系统**先把能做的做好了**，把**要他拍板的收到一个地方**。

> P0 只做「当前项目 + 当前标段」推进。项目级一键推进多个标段放到 P2，避免第一版就要处理多标段 fan-out、部分失败和跨标段待办聚合。

## 3. 能力（Tool）与决策（Agent/Harness）分离——但全在后台

| 目录 | 职责（后台管道，不暴露给用户） | 关键约束 |
|---|---|---|
| `tools/` | 工具注册表：把 service 包成带输入/输出 schema、自动写 audit 的 Tool | LLM 只能从白名单挑；参数过 schema 校验；禁止自由拼 SQL / URL（复用 `url_safety`） |
| `agents/` | 角色 Agent：证据绑定 / 草稿 / 自检 | 只产「建议 + 理由 + 来源」，绝不越过人确认自动落库为 `confirmed` |
| `harness/` | 有界编排引擎：跑一次「推进」 | `max_steps` + 终止条件；写 `AsyncTask(task_type=assist_evidence)`；卡住 / 低置信 / 检索为空 → 不推进，把该项标成「待办」交回人 |

## 4. 合规护栏（硬性）

1. **建议 ≠ 生效**：Agent 产建议，证据绑定 / 资质结论 / 最终稿必须人确认才生效。
2. **有界 + 兜底**：循环有步数上限、明确终止条件；置信低 / 检索空 / 工具报错 → 停下交回人。
3. **全链可追溯**：复用 `app/audit`，每个 Tool 调用写一条 `AuditLog(actor_type=agent)`，可回放：哪个 Agent、调了什么、输入摘要、输出、引用来源。
4. **工具白名单 + 输入校验**：LLM 决定调哪个工具，参数经 Pydantic 校验后才执行。
5. **来源不可编造**：`source_ref` 只能来自检索命中的 material / chunk / snippet / metadata；LLM 只负责生成自然语言理由，不允许生成页码、文件名或块号。

## 5. 第一个纵切片：证据绑定（就地建议）

> 先打通这一条最窄链路，验证「一键触发 → 就地建议 → 就地采纳 → 审计」这套骨架与体验，再按同模式扩 草稿、自检。

### 5.1 复用的现有能力（不重写）

- `recommend_compliance_evidence_candidates`（`routes/projects.py:4383`）：按合规项检索候选材料、过滤已绑定、按数据级别/确认状态过滤。
- `search_material_hits` / `material_retrieval`：底层混合检索 + rerank。
- `compliance_item_candidate_query`（`projects.py:280`）：合规项 → 检索 query。
- `bind_compliance_evidence`（`4533`）/ `confirm_compliance_item`（`4243`）：**人采纳后**的落库路径（建议复用，不另起一套绑定逻辑）。
- `compliance_priority_for_item` / `enterprise_evidence_summary_for_item`：优先级与证据汇总。

### 5.2 后台 Agent 做什么

1. **选目标**：harness 列出「缺证据 / 证据不足」的合规项，按 `compliance_priority_for_item` 排序（先做高优先 + 强制项）。
2. **逐项找证据**：调候选证据工具拿 top-k 命中。
3. **产建议**：对 top-k 用 LLM 产一句「为什么这条能响应该合规项」，来源字段直接使用检索 hit 的 `material_id/chunk_id/snippet/metadata`，存为建议（**不落 binding**）。
4. **写审计**：`AuditLog(actor_type=agent, action="evidence.suggested")`。
5. **回到 UI**：该合规项行内出现 💡 建议；同时进「待办」计数。**不自动绑定**。

### 5.3 数据模型增量（后台）

新增建议表，把「建议态」与「生效态」分开，**不污染** `ComplianceEvidenceBinding`：

```
agent_evidence_suggestions
  id, tenant_id, project_id, section_id, compliance_item_id
  async_task_id (nullable FK)   -- 关联本次后台推进任务；用户不可见，但用于排障/回放
  run_key (str)                 -- 本次推进的内部批次号，便于 supersede 同批旧建议
  enterprise_material_id
  material_snapshot (JSONB)    -- 候选材料快照
  candidate_rank (int)          -- top-k 排名
  score (float)                -- rerank 后分数
  reason (text)                -- LLM 命中理由（仅辅助人判断，不作绑定依据）
  source_ref (JSONB)           -- 来源文件/页码/块号；只能来自检索 hit，不能由 LLM 编
  query_hash (str)             -- 生成该建议时的 query 指纹，用于判断陈旧
  status (str)                 -- suggested | accepted | dismissed | superseded
  created_at / decided_at / decided_by
```

> 故意不建用户可见的 `agent_run` 控制台。后台仍保留 `async_task_id/run_key`，用于任务句柄、审计回放、重跑覆盖和失败排查；用户只看到「后台任务状态 + 完成提示」。

状态机：

- `suggested -> accepted`：用户采纳；同一合规项的其他 `suggested` 建议置 `superseded`。
- `suggested -> dismissed`：用户忽略；必须写原因或使用默认原因，进入审计。
- `suggested -> superseded`：合规项已被人工绑定、材料变为过期/冲突、或新一轮推进产生了更新建议。
- 只有 `suggested` 能被 accept/dismiss；接口需做乐观检查，避免重复点击和多人并发导致重复绑定。

采纳事务规则：

1. 重新读取 suggestion、compliance item、enterprise material，并确认三者仍属于同一 tenant/project/section。
2. 检查 suggestion 仍为 `suggested`，material 未过期/冲突，且该合规项未绑定等价材料。
3. 调用现有绑定落库路径（复用 `bind_compliance_evidence` 内部逻辑或抽成 service），成功后 suggestion 置 `accepted`。
4. 如绑定被拒绝，不吞错自动成功；返回可理解错误，并视情况把 suggestion 置 `superseded`。

### 5.4 API 表面（尽量薄；不新增用户要学的页面）

- `POST /projects/{project_id}/sections/{section_id}/assist`：触发当前标段的一次推进（异步，复用现有 `AsyncTask` / `task_dispatch` / inline fallback）。返回 `AsyncTaskRead`，前端轮询出「完成，N 项待确认」。
- 建议**就地呈现**：扩展**现有**合规项读取 / 候选证据返回，带上该项最新的 `agent_suggestion`（status=suggested）。**不新增独立提案页**。
- `POST /projects/{project_id}/sections/{section_id}/compliance-items/{item_id}/evidence-suggestions/{sid}/accept`：人采纳 → 内部走现有绑定逻辑 + 建议置 `accepted`。
- `POST /projects/{project_id}/sections/{section_id}/compliance-items/{item_id}/evidence-suggestions/{sid}/dismiss`：忽略 + 原因写审计。
- 待办来源（P0 明确）：合规项列表返回 `agent_suggestion` 后，前端把 `status=suggested` 的建议加入现有 `homeTodoRows` / 工作区待办队列；如后续要跨页面统一，由 P1 抽成 `GET /projects/{project_id}/sections/{section_id}/todo-summary`。

### 5.5 审计增量

`AuditLog.actor_type` 当前 CheckConstraint 只允许 `user/system/worker`，需加 `agent`（一条迁移）。新增 action：`evidence.suggested` / `evidence.suggestion_accepted` / `evidence.suggestion_dismissed` / `assist.started` / `assist.finished` / `assist.failed`。

审计内容约束：

- Tool 调用审计只存输入摘要、输出摘要、来源引用和耗时，不存完整 prompt / 大段原文。
- accept/dismiss 审计的 `actor_type=user`，suggest/started/finished/failed 审计的 `actor_type=agent` 或 `system`。
- `AuditLog.actor_user_id` 对 Agent 行可为空；如由某用户点击触发，可在 `after_json.triggered_by` 里记录触发用户。

### 5.6 数据库/异步任务迁移清单

P0 至少需要这些迁移和模型同步：

1. 新增 `agent_evidence_suggestions` 表及索引：`tenant_id/project_id/section_id/compliance_item_id/status/created_at`，并对 `async_task_id` 建索引。
2. 扩展 `audit_logs.actor_type` CheckConstraint：加入 `agent`。
3. 扩展 `async_tasks.task_type` CheckConstraint：加入 `assist_evidence`。
4. `worker.py` 增加 `tasks.assist_evidence`；开发环境继续支持 `RUN_TASKS_INLINE=true` 的 inline/background fallback。
5. 新增 schema：`AgentEvidenceSuggestionRead`、`EvidenceSuggestionAcceptRequest`、`EvidenceSuggestionDismissRequest`，并把 `ComplianceItemRead` 扩展一个可空 `agent_suggestion`。

## 6. harness / tool 最小骨架

- `tools/registry.py`：`Tool` 抽象（name、input/output schema、`run(ctx, params)` 自动写 audit）。第一切片只注册 `retrieve_evidence_candidates`、`summarize_evidence_reason`(LLM)。`summarize_evidence_reason` 的输入必须包含检索 hit，输出只允许 `reason`，不允许输出 `source_ref`。
- `harness/runner.py`：一次「推进」的有界执行（`planning → executing → done/failed`），带 `max_steps`、超时、异常兜底；产出建议即结束，**不阻塞等人**（人异步在 UI 里就地处理）。最终写 `AsyncTask.output_json={suggested_count, todo_count, skipped_count, error_count}`。
- `agents/evidence_binding.py`：编排上面两个 tool 的角色 Agent。

## 7. 分期落地

1. **P0（本切片）**：tool 注册表 + harness 最小版 + 证据绑定 Agent + 建议表 + `assist_evidence` 异步任务 + 就地建议/采纳接口 + audit `agent` 类型。前端：当前标段「让 Agent 帮我推进」按钮 + 合规矩阵行内建议 + 待办计数接入现有 `homeTodoRows` / 工作区待办。
2. **P1**：草稿 Agent（已确认证据上产草稿，就地出现在现有草稿审阅里）+ 自检 Agent（覆盖/事实校验产待办，进同一个待办队列）。
3. **P2**：把「推进」做成可重复运行的一键体验（跑完只增量提示新待办）；按需提供「Agent 怎么得出的」详情抽屉（渐进展开，默认收起）。

## 8. 风险与未决

- **LLM 理由可信度**：理由只辅助人判断，不作绑定依据；UI 明示「建议，需人核」。
- **成本/时延**：逐项 LLM 产理由可能慢——批量 + 缓存 + 只对 top-k 产理由 + 异步跑。
- **与批量确认不分叉**：采纳一律复用现有 bind/confirm 路径。
- **就地建议不打扰**：建议要可一键「全部忽略」，避免矩阵被建议刷屏。
- **多标段推进暂不做**：P0 只处理当前标段；项目级推进到 P2 再处理跨标段任务聚合与部分失败。
- **换一条的语义**：P0 可先做「同一 top-k 候选切换」；如要重新检索/重新产理由，放 P1。

## 9. 验收口径

- 当前标段点「让 Agent 帮我推进」→ 生成 `assist_evidence` 异步任务，后台跑完提示「N 项待确认」，**不自动绑定**。
- 缺证据的高优先合规项**行内**出现建议（含理由 + 来源），点「采纳」走现有绑定路径落库；「忽略」原因入审计。
- 待办计数正确反映 Agent 建议；用户全程不接触 run/proposal 这类概念。
- 来源字段来自检索命中的 material/chunk/snippet；测试需覆盖 LLM 输出无法覆盖 `source_ref`。
- 后端测试：建议生成、accept→bind、dismiss、重复 accept、材料过期/冲突、harness 兜底（检索空/工具异常时该项标为待办而非报错）。
