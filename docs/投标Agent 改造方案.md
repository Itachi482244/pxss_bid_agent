# 投标 Agent 改造方案

> 更新时间：2026-06-19
> 状态：Stage 0-3 已接入主流程；ToolSpec 与只读 LLM 子 Agent 为基础模块，主流程尚未调用
> 参考：`docs/free-code Agent能力技术拆解与可复制设计.md`、`docs/投标Agent 标书内容打磨主轴设计.md`
> 关联代码：`backend/app/services/agent_assist.py`、`backend/app/services/qualification_evaluation.py`、`backend/app/worker.py`、`backend/app/models/agent.py`、`backend/app/models/task.py`

---

## 0. 定调结论（决定整个方案方向）

本项目的产品价值是 **L1–L3 的确定性正确（防废标 / 不丢分）**，不是"让 LLM 写漂亮散文"。这一点在 `投标Agent 标书内容打磨主轴设计.md` 已确立：**标书价值的 70% 在 L1–L3（确定性、可校验），只有 30% 在 L4（生成式）**。

因此本次改造的核心判断：

> **不能**把 `agent_assist` 改造成 free-code 那种"LLM 主循环 + 工具委派"的通用 Agent。
> **正确做法**是借鉴 free-code 的**工程骨架**（统一 Tool 协议、角色/步骤配置化、任务状态机、权限治理、结果预算），把当前**写死的规则流水线**升级为"**可配置、可观测、可治理、可扩展**"的编排器；同时预留一个**干净的接缝**，未来仅在 L4 / 判断类、非确定性环节按需插入"只读、只产建议"的 LLM 子 Agent。

一句话：**借它的架构模式，不借它的 LLM 链路。**

---

## 1. 现状盘点

### 1.1 当前"Agent"是什么

当前 `execute_agent_assist_task`（`agent_assist.py`）是一个**确定性规则流水线**，由 Celery 任务 `tasks.agent_assist` 驱动，固定执行三步：

```
matrix_review  →  evidence_binding  →  qualification_technical
（条款例外审阅）   （证据绑定建议）       （资格/技术/草稿待确认）
```

产物是 `AgentReviewItem`（例外式"待人工拍板"清单），通过 `requires_human` / `severity` / `status(open|auto_passed|...)` 表达人机边界。它**不是** LLM agent——没有模型主循环、没有工具调用协议、没有子 Agent 委派。

### 1.2 现状逐维度评估

| 维度 | 现状 | 痛点 |
|---|---|---|
| 编排 | 三步顺序、阈值（`AUTO_PASS_CONFIDENCE` 等）写死在 `execute_agent_assist_task` 与各 `_add_*_review_items` | 步骤/顺序/阈值不可配置，无法单独测试/灰度单步 |
| 能力 | `search_material_hits`、`run_qualification_evaluation`、`_confirm_*` 等直接散调 | 无统一契约，无法声明只读/破坏性/权限，无法复用到未来编排 |
| 人工边界 | `requires_human`、`_severity_for_item`、`_confirmation_requires_source_verified` 等 | 判定规则埋在 ~1400 行大函数的隐式分支里，难维护、难审计 |
| 任务 | `AsyncTask` + Celery；已有幂等键、active 唯一索引、`progress`、`output_json` | `progress` 仅 5/20/50/80/100 粗档；无"当前在做什么"的活动描述 |
| 治理 | 有 `actor_type=agent/user` 审计区分；`_confirmation_requires_source_verified` 门槛 | "哪些动作可 Agent 自动 / 哪些必须人工 / 哪些禁止"无集中声明 |
| 并发 | `uq_async_tasks_agent_assist_active_section` 偏唯一索引 + `_find_inflight_agent_assist_task` | 已较稳健，保留 |

### 1.3 已知问题对照（Bugbot 三处告警）

最近一次 Bugbot 审查报告三个 high 级问题，均源于"判定规则散落在大函数里"：

1. **重评估后确认状态陈旧**（`qualification_evaluation.py:619-628` 一带）：当前代码其实已通过 `confirmation_stale`（`_evaluation_result_changed` 为真时清除 `confirmed_by/confirmed_at/confirm_reason`，见 `qualification_evaluation.py:668-671`）部分处理。
2. **已确认评估被重开待办**（`agent_assist.py:664-704`）：当前代码已在 `evaluation.confirmed_by is not None` 时产出 `auto_passed` 的"preserved"项并 `continue`（`agent_assist.py:669`）。
3. **并发 assist 任务竞态**（`projects.py:2367-2417`）：已有 active 偏唯一索引 + `IntegrityError` 回捕兜底。

> 结论：三处问题当前都有**隐式**防护，但都依赖大函数内的分支与索引约束，**缺乏集中声明与专项测试**。本方案通过 `ActionPolicy` + 金标准测试把它们显式化、钉死。

---

## 2. 目标架构

### 2.1 总览

```
AgentOrchestrator  (execute_agent_assist_task 瘦身后)
        │  读取 AssistPlan(配置：启用哪些 step、各 step 的阈值与 runner)
        ▼
  ┌─ Step: matrix_review        ─┐
  ├─ Step: evidence_binding     ─┤→ 每个 Step 是纯函数 runner，调用若干 Tool
  └─ Step: qualification_tech   ─┘
        │
        ├─ ToolSpec (统一能力契约)        ── EvidenceSearchTool / QualificationEvaluateTool / ...
        │     is_read_only / is_destructive / check_permission / run
        │
        ├─ ActionPolicy (集中决策)        ── 每个 action 的 automation: auto|human|deny + severity 规则
        │
        ▼
  AgentReviewItem  (产物结构不变，向后兼容)
        │
        ▼
  AsyncTask  (沿用 Celery；ProgressReporter 细化 progress + 当前活动)
```

### 2.2 四个新抽象（均为纯 Python、可单测、零 LLM 依赖）

| 抽象 | 文件（建议） | 借鉴 free-code | 作用 |
|---|---|---|---|
| `ActionPolicy` | `app/services/agent/policy.py` | §13 PermissionResult、§16.5 动作分级 | 集中声明每个 action 能否自动、是否需核验来源、severity 规则 |
| `AssistStepDefinition` / `AssistPlan` | `app/services/agent/definitions.py` | §8 AgentDefinition、§16.2 配置化 | 步骤/角色配置化，编排器只遍历 plan |
| `ToolSpec` | `app/services/agent/tools/base.py` | §6 Tool 协议、§16.1 | 统一能力契约，声明只读/破坏性/权限 |
| `ProgressReporter` | `app/services/agent/progress.py` | §11.2 ProgressTracker | 细化任务进度与活动描述 |

### 2.3 设计原则（取自 free-code §17 可复制清单的子集）

1. **能力即边界**：所有副作用经过 Tool 契约，声明 `is_read_only` / `is_destructive`。
2. **配置化角色**：步骤、阈值、是否启用都进配置，不写死在编排函数。
3. **集中权限**：自动/人工/拒绝在一处声明，不散落分支。
4. **运行态集中注入**：runner 依赖通过 `StepContext` 注入，不依赖全局/隐式状态（free-code §6.2 ToolUseContext 思路）。
5. **建议 ≠ 生效**：Agent 只产 `AgentReviewItem` 建议，人工拍板后才落库——与主轴护栏第 4 条一致。
6. **结果预算**：大 JSON 截断 + 保留引用，防止产物膨胀。
7. **不臆造**：继承主轴第一护栏，缺事实留占位/缺口，绝不编。

---

## 3. 分阶段实施方案

> 当前落地顺序：阶段 0 → 1 → 2 → 3 → 4 → 5。LLM 子 Agent 统一复用主 Agent 的 `chat_completion` 配置解析链路，不单独保存或传入 base_url/api_key。

### 阶段 0：固化金标准测试（约 0.5 天，零风险）

**目的**：重构前先建回归网，保证产物 100% 向后兼容。

**做什么**：
- 构造一组固定输入（一批 `ComplianceItem` + 证据绑定 + 资格项），跑当前 `execute_agent_assist_task`，把产出的 `AgentReviewItem` 集合（按 `step/action/status/severity/requires_human` 维度）固化为断言基线。
- 覆盖：matrix 例外 vs 低风险自动通过、缺证据、证据建议、资格评估 open/auto_passed/preserved、技术响应、草稿 block。

**产出**：`backend/tests/test_agent_assist_golden.py`（新增）。

**验收**：测试通过，且能在后续每个阶段重复运行不变。

---

### 阶段 1：动作权限集中化 `ActionPolicy`（约 1 天，高收益）

**目的**：把散落的"能否自动 / 是否需核验来源 / severity"收敛到一张表，显式修复 Bugbot 类问题。

**新建** `backend/app/services/agent/policy.py`：

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Literal

Automation = Literal["auto", "human", "deny"]

@dataclass(frozen=True)
class ActionPolicy:
    action: str
    default_automation: Automation          # 默认自动化级别，具体目标可覆盖
    note: str = ""

ACTION_POLICIES: dict[str, ActionPolicy] = {
    "agent_matrix_low_risk_pass":      ActionPolicy("agent_matrix_low_risk_pass", "auto", note="低风险、来源明确，仅记录不改状态"),
    "confirm_matrix_item":             ActionPolicy("confirm_matrix_item", "human"),
    "review_technical_response":       ActionPolicy("review_technical_response", "human"),
    "accept_evidence_binding":         ActionPolicy("accept_evidence_binding", "human"),
    "missing_evidence":                ActionPolicy("missing_evidence", "human"),
    "review_qualification_evaluation": ActionPolicy("review_qualification_evaluation", "human"),
    "confirm_qualification_decision":  ActionPolicy("confirm_qualification_decision", "human"),
    "review_draft_block":              ActionPolicy("review_draft_block", "human"),
    "ack_llm_technical_advice":         ActionPolicy("ack_llm_technical_advice", "human", note="只读建议，采纳仅关闭建议"),
    "ack_llm_draft_advice":             ActionPolicy("ack_llm_draft_advice", "human", note="只读建议，采纳仅关闭建议"),
    # 未来：export_tender_format_docx -> ActionPolicy(..., "human") 且要求 preflight 通过
}

def policy_for(action: str) -> ActionPolicy: ...

class AgentActionPolicy:
    def requires_source_verified(self, action: str, target: object | None = None) -> bool: ...
    def automation_for(self, action: str, target: object | None = None) -> Automation: ...
```

**配套**：将 `_severity_for_item` 与 `_confirmation_requires_source_verified` 迁移/对接到此模块，`accept_agent_review_item` 在落库前统一查 context-aware `requires_source_verified(action, target)`。

**借鉴**：free-code §13.1（权限结果非 bool）、§16.5（动作分级）。

**验收**：阶段 0 金标准测试不变；新增策略测试断言 action 的自动化级别与上下文来源核验要求。

---

### 阶段 2：步骤配置化 `AssistPlan`（约 2 天，核心）

**目的**：编排器与具体步骤解耦，步骤可启用/停用/调阈值/单测。

**新建** `backend/app/services/agent/definitions.py`：

```python
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable

@dataclass
class StepContext:
    db: "Session"
    project: "Project"
    section: "BidSection"
    items: list["ComplianceItem"]
    evidence_counts: dict
    run_key: str
    async_task_id: "uuid.UUID | None"
    actor_user_id: "uuid.UUID"
    report: "ProgressReporter"

@dataclass(frozen=True)
class AssistStepDefinition:
    step: str
    when_to_use: str
    runner: Callable[[StepContext], list["AgentReviewItem"]]
    auto_pass_confidence: Decimal = Decimal("0.8800")
    enabled: bool = True

@dataclass(frozen=True)
class AssistPlan:
    steps: list[AssistStepDefinition]

DEFAULT_ASSIST_PLAN = AssistPlan(steps=[
    AssistStepDefinition("matrix_review", "条款覆盖与低风险自动核验", run_matrix_review),
    AssistStepDefinition("evidence_binding", "缺证据暴露与候选证据建议", run_evidence_binding),
    AssistStepDefinition("qualification_technical", "资格/技术/草稿人工拍板项", run_qualification_technical),
])
```

**改造** `execute_agent_assist_task`：瘦身为"遍历 `plan.steps` → 调 `runner(ctx)` → 收集 items → 汇总 → 落 `AsyncTask`"。现有三个 `_add_*_review_items` 重构为 runner 纯函数，依赖经 `StepContext` 注入。

**借鉴**：free-code §8（AgentDefinition）、§16.2（配置化）、§6.2（运行态集中注入）。

**验收**：阶段 0 金标准测试不变（产物等价）；新增按 step 的单测；可通过 `enabled=False` 跳过单步并验证产物差异。

---

### 阶段 3：任务进度与结果预算（已落地）

**目的**：提升可观测性，防止产物膨胀。

**做什么**：
1. 新建 `app/services/agent/progress.py` 的 `ProgressReporter`：把 `AsyncTask.progress` 从粗档升级为"已处理 N/总 M 条 + 当前 step + 当前活动描述"，写入 `output_json.progress`（结构化）。借鉴 free-code §11.2 `ProgressTracker`。
2. 对 `recommendation_json` / `reasons_json` 加**结果预算**：超过字符/条数阈值时截断并保留引用（如只存 id + 摘要），避免 `AgentReviewItem` 行无限膨胀。借鉴 free-code §5.2（大结果替换为引用）、§17.8。

**验收**：前端轮询能看到实时进度；新增测试断言超长 JSON 被截断且保留可追溯引用。

---

### 阶段 4：统一 Tool 协议（已落地）

**目的**：把现有能力包装成统一契约，声明只读/破坏性/权限，为阶段 5 接入 LLM 子 Agent 做前置。

**已新建** `backend/app/services/agent/tools/base.py`：

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class PermissionResult:
    decision: str            # allow | deny | ask
    reason: str = ""

@dataclass
class ToolResult:
    ok: bool
    data: dict
    preview: str = ""        # 大结果截断后的预览（结果预算）

class ToolSpec(Protocol):
    name: str
    def is_read_only(self) -> bool: ...
    def is_destructive(self) -> bool: ...
    def check_permission(self, input: dict, ctx) -> PermissionResult: ...
    def run(self, input: dict, ctx) -> ToolResult: ...
```

**首批工具（只加壳，不改实现）**：
- `EvidenceSearchTool` 包 `search_material_hits`（`is_read_only=True`）。
- `QualificationEvaluateTool` 包 `run_qualification_evaluation`（非只读、非破坏）。
- `ComplianceConfirmTool` 只允许用户确认上下文执行，并统一转入 `accept_agent_review_item`，保证 `AgentReviewItem` 状态、审计和业务对象在同一采纳路径流转。

**借鉴**：free-code §6（Tool 协议）、§6.1（保守默认值：并发安全/只读默认 false）、§16.1。

> ROI 提示：纯规则形态下本阶段主要价值在于能力契约和未来工具治理；当前只作为显式工具壳落地，不默认接入主 runner。

**验收**：被包装能力的现有调用方行为不变；已新增工具契约单测（只读/写建议状态/用户确认写入/权限断言）。

---

### 阶段 5：LLM 子 Agent 接缝（已落地基础实现）

**目的**：仅在**判断类、非确定性**环节引入 LLM，且严格"只读、只产建议"。

**适用场景**：
- L4 叙述骨架的风格润色建议（受 L1–L3 已确认事实约束）。
- 技术响应/偏离的初判建议（仍由人工确认偏离结论）。

**护栏（free-code §15.2 只读双保险）**：
- prompt 强约束 + `disallowedTools`：**禁止**子 Agent 写正式稿、导出、绑定证据、确认资格。
- 产物仍走 `AgentReviewItem`（建议态），人工查看/关闭建议；不得借 accept 隐式触发真实业务动作。
- 继承主轴"不臆造"护栏：不许编造证据/页码/指标/工程量。
- LLM 调用统一走 `app.services.llm_gateway.chat_completion`，由 `resolve_chat_model_config` 读取租户模型配置或环境变量，不允许子 Agent 另传独立 base_url/api_key。

**借鉴**：free-code §15.2（Explore 只读 Agent）、§16.5（最小权限）、§13.3（无法弹 UI 时自动 deny / bubble）。

**验收**：子 Agent 在任何路径下都无法产生落库副作用；其建议只包装成 `ack_llm_technical_advice` / `ack_llm_draft_advice` 待办，人工 accept 仅关闭建议并写审计，不确认条款、不绑定证据、不批准草稿。

---

## 4. 明确不做（避免过度工程）

| 不做项 | 理由 |
|---|---|
| 用 free-code `query()` LLM 主循环替换规则流水线 | 把确定性、可控的系统变成不可控；与"防废标"价值正交 |
| AgentTool 递归委派 / fork / teammate / swarm | 当前阶段过重，无对应业务需求 |
| React/Ink UI、完整 OTel tracing、feature flag 体系 | 后端优先系统不需要；保留现有 `AuditLog` 即可 |
| fork prompt cache | 高级且复杂，第一版不碰 |

（与 free-code 文档 §18"不建议直接照搬"一致。）

---

## 5. 风险与护栏

| 风险 | 护栏 |
|---|---|
| 重构破坏产物兼容 | 阶段 0 金标准测试钉死；每阶段重跑 |
| 并发重复任务 | 保留 `uq_async_tasks_agent_assist_active_section` 唯一索引 + `IntegrityError` 回捕 |
| 已确认项被覆盖/重开 | 规则收敛到 `ActionPolicy` + `confirmation_stale`，加专项测试 |
| 引入 LLM 后臆造 | 子 Agent 只读、只产建议、人工拍板；继承主轴"不臆造"护栏 |
| 改造范围蔓延 | 严格按"明确不做"清单收口 |

---

## 6. 工作量与排期建议

| 阶段 | 内容 | 预估 | 依赖 |
|---|---|---|---|
| 0 | 金标准测试 | 已落地 | 无 |
| 1 | `ActionPolicy` 集中化 | 已落地 | 阶段 0 |
| 2 | `AssistPlan` 配置化 | 已落地 | 阶段 0/1 |
| 3 | 进度 + 结果预算 | 已落地 | 阶段 2 |
| 4 | Tool 协议 | 已落地 | 阶段 2 |
| 5 | LLM 子 Agent 接缝 | 已落地基础实现 | 阶段 4 |

**主干（0+1+2+3）已落地**，纯收益、零 LLM 依赖。阶段 4/5 已完成基础接缝与护栏，后续可按业务入口决定是否把 LLM 建议接入具体 assist step。

---

## 7. 目录骨架（落地后）

```
backend/app/services/agent/
  policy.py          # ActionPolicy：自动/人工/拒绝集中决策
  definitions.py     # AssistStepDefinition / AssistPlan / StepContext
  progress.py        # ProgressReporter：进度与活动描述
  llm_subagent.py    # 只读 LLM 子 Agent 接缝，复用主 Agent LLM 配置
  tools/
    base.py          # ToolSpec / PermissionResult / ToolResult
    evidence_search.py
    qualification_evaluate.py
    compliance_confirm.py
# agent_assist.py 保留兼容入口，并承载当前 step runner 函数 + accept/dismiss 入口
```

---

## 8. 与现有设计的衔接

- **与主轴设计**：本方案是"半自主推进（4/5/6 步）"编排层的工程化重构，不改变 L1–L4 装配链路（`tender_format_*`）与"建议≠生效""不臆造"护栏。
- **与数据层**：`AgentReviewItem`、`AsyncTask`、`QualificationEvaluation` 等模型结构**不变**，仅重构生成它们的服务层逻辑，确保平滑迁移。
