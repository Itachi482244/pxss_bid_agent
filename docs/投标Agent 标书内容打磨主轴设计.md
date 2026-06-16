# 投标 Agent 标书内容打磨主轴设计（合规覆盖 L1–L4）

> 更新时间：2026-06-16
> 状态：核心链路已接入（L1 证照嵌入、L2 评分索引、L3 偏离/报价校验、L4 事实约束叙述骨架已接入；评分索引页码通过 Word 书签/PAGEREF 域回填）
> 目标：把"产出一份能投、不废标、不丢冤枉分的标书"做成应用的**核心交付能力**，并给出可逐层深化的工程主轴。
> 不做：把"内容打磨"等同于"让 LLM 写得漂亮"；在合规/评分/偏离/报价四层没打牢前先堆散文。

## 0. 第一原则：先定义"内容"，再谈"打磨"

标书内容是这个应用**唯一真正交付给用户的东西**——解析、目录推导、信号抽取都是为它服务的中间件。但"打磨内容" ≠ "文笔好"。

从中标级样张（`仓顶面吊顶隔热降温改造投标文件.pdf`）反推：决定标书成败的从来不是叙述文采，而是分层的**确定性正确**。一份文笔满分、却漏了营业执照或偏离表标错一条的标书，照样废标。

因此本设计的核心判断：

> **标书内容价值的 70% 在 L1–L3（确定性、可校验、防废标），只有 30% 在 L4（生成式散文）。投入顺序必须先 L1–L3，后 L4。**

### 0.1 内容质量四层模型

| 层 | 它决定什么 | 性质 | 写错的后果 |
|---|---|---|---|
| **L1 合规格式** | 必备表单/附件/证照齐全、强制条款应答、签章到位 | 确定性，可校验 | **直接废标**——文笔再好也没用 |
| **L2 评分覆盖** | 评分办法每个评分点都有应答 + 证据 + 索引指向 | 半确定性 | 漏一条＝丢一档分 |
| **L3 偏离响应** | 技术参数逐条响应、工程量清单算术、不超预算 | 确定性 | 丢分或废标 |
| **L4 实质叙述** | 施工组织设计、技术方案、服务承诺等散文 | 生成式 | 影响主观分 |

L1–L3 是"投得出、不出错"的底线（table stakes，必须接近 100%）；L4 是"写得有竞争力"的差异化。**底线没守住前，差异化无意义。**

### 0.2 关键洞察：样张是"模板装配"，不是"自由写作"

仓顶中标样张几乎没有 L4 散文，整份是：填好的格式表单（响应声明/授权委托书/身份证明）＋ 证照扫描件 ＋ 结构化表格（偏离表/报价表）＋ 评分索引。这决定了产出路径是**模板装配 + 覆盖校验**，而非 LLM 长文生成。

## 1. 架构主轴与数据流

内容产出拆成五个**纯函数、无 I/O / 无 DB** 的可单测模块，串成一条装配管道：

```
招标正文(解析拍平)
   │
   ├─ tender_directory.derive_directory()        → 目录大纲 + 招标信号（份数/有效期/包号…）
   │
   ├─ tender_outline.map_nodes_to_chapters()     → [{section_type, title, attachments}]
   │
   ├─ tender_format_templates.extract_format_templates()
   │       → {模板键: FormTemplate(含填空位 slots)}    （声明/委托书/身份证明…）
   │     .fill_template(模板, facts)
   │       → FilledTemplate(填好的行 + 未填清单)        （缺事实留『［待填:字段］』占位）
   │
   ├─ tender_compliance_coverage.compute_coverage()
   │       → CoverageReport(L1 完整 / L2、L3 骨架)      ← 本设计新增层
   │
   └─ tender_format_assembler.assemble_format_docx()
           → 投标文件 docx（响应文件组成 + 合规自检清单 + 逐章渲染）
```

### 1.1 模块职责

| 模块 | 职责 | 状态 |
|---|---|---|
| `tender_directory` | 从"响应文件组成/格式"章推导目录、抽招标信号 | 已完成（含动态目录） |
| `tender_outline` | 目录节点 → 章节类型 + 附件清单 | 已完成 |
| `tender_format_templates` | 抽取格式表单、识别填空位、按事实填充（含上下文消歧） | 已完成 |
| `tender_compliance_coverage` | L1/L2/L3 三层"要求→应答覆盖"统一报告 | L1 完整；L2/L3 已优先消费 `ComplianceItem`/证据绑定 |
| `tender_format_assembler` | 按推导目录装配 docx，渲染自检清单与各章 | 已完成审阅/正式双模式，支持证照嵌入、评分索引、偏离/报价表 |

### 1.2 事实来源（已摸清）

填充事实由 `tender_format_assembler.build_form_facts()` 把 `_project_facts` + `outline.signals` 适配成模板引擎的 `field_key`：

- **项目/招标信息**：采购人、项目名称、采购代理编号（来自 Project / section / 招标信号）。
- **企业信息**：供应商名称、法定代表人、授权代理人、统一社会信用代码、地址（来自 EnterpriseProfile）。
- **签字代表**：优先授权代理人，回退法定代表人。
- **份数/有效期/包号**：来自招标信号（`copies` → 副本份数等）。
- **已知缺口**：邮编、电话、电子邮箱、包号、性别/年龄/职务、委托期限 —— 缺则留占位，由人补齐（绝不臆造）。

## 2. 已有合规基础设施（复用，不重造）

数据层早已存在一套"要求→应答覆盖"骨架，本主轴的本质是**把装配器接到这套数据上**，而非另起炉灶：

| 已有件 | 角色 |
|---|---|
| `ComplianceItem`（`item_type` ∈ qualification / mandatory_response / format / deadline / scoring / technical_response …） | "要求"层：L1/L2/L3 的条目来源 |
| `ComplianceEvidenceBinding`（ComplianceItem → EnterpriseMaterial） | "应答/证据"层：覆盖边 |
| `EnterpriseMaterial`（扫描件存 MinIO：`bucket` / `object_key` / `content_type`） | 证照嵌入的原料 |
| `build_preflight_check`（缺证据计数 / 高风险未确认 / 强制项缺口） | 缺口报告雏形 |
| `recommend_compliance_evidence_candidates` / `search_material_hits` | 证据候选检索（半自主推进已用） |

> 当前 `tender_format_assembler` 仍保持 B 路径独立装配器的低耦合形态，但导出链路已把 Project/Section 事实、`ComplianceItem`、`ComplianceEvidenceBinding` 与可嵌入的 `EnterpriseMaterial` 快照接入装配器；装配器本身继续保持无 DB / 无 I/O，便于单测和审阅/正式双模式复用。

## 3. 已落地：L1 合规覆盖骨架 + 自检清单

### 3.1 覆盖模型（`tender_compliance_coverage.py`）

```
CoverLayer   = L1 合规格式 | L2 评分覆盖 | L3 偏离响应
CoverStatus  = fillable(可自动填) | partial(部分待补) | needs_material(需上传材料)
             | ready(材料已备) | missing(缺失) | pending(待应答)
CoverageItem = {layer, title, status, detail, disqualifying(是否废标项)}
CoverageReport.gaps / .disqualifying_gaps / .summary()
```

- **L1 完整计算**：
  - 必备表单（声明/委托书/身份证明）：按 `fill_template().unfilled` 判 `fillable` / `partial`，并列出待补字段。
  - 附件/证照：按标题关键词分类（营业执照/资质/信用/业绩…），判定是否为核心资格（`disqualifying`）；与企业材料库可用材料粗匹配 → `ready` / `needs_material`。
  - 本文档内生成的表单/表格（报价一览表/偏离表等）不计入"需上传材料"。
- **L2 覆盖**：优先消费 `ComplianceItem(item_type=scoring)` 与 active 证据绑定；没有绑定则保持 `pending`，进入评分索引和审阅缺口。
- **L3 覆盖**：优先消费 `ComplianceItem(item_type=technical_response)` 生成偏离/响应行；具体我方响应和偏离结论仍由人工确认，未知内容不补写。

### 3.2 装配器渲染

`assemble_format_docx` 在"响应文件组成"后插入**「合规自检清单」**页：

- 顶部废标风险**红牌**：有核心资格缺口则列出，否则显示"暂未发现废标风险"。
- 分层状态表：`层级 | 条目 | 状态 | 说明`，★标核心资格/废标项。
- 附件章每条行内追加状态标注（如 `［需上传材料·废标风险］`）。

### 3.3 仓顶样张验证结果

```
L1 合规格式: {partial: 3, ready: 2, needs_material: 1}
L2 评分覆盖: {pending: 3}      （投标价格30分 / 技术部分50分 / 类似业绩）
L3 偏离响应: {pending: 1}      （技术/商务响应与偏离表）
废标风险缺口: 无               （营业执照、信用查询已匹配材料库）
```

自检清单逐行（节选）：

| 层级 | 条目 | 状态 |
|---|---|---|
| L1 | 磋商响应声明 | 部分待补：邮编、电话、电子邮箱、包号 |
| L1 | ★附件2-1 营业执照等主体资格证明 | 材料已备 |
| L1 | ★附件2-2 信用查询 | 材料已备 |
| L1 | 附件2-3 特定资格条件证明 | 需上传材料 |

测试覆盖：`backend/tests/test_tender_compliance_coverage.py`（7 项），含表单可填/待补、附件需材料/废标缺口、L2/L3 骨架行、汇总分组。

## 4. 路线图：逐层深化

按"先底线后差异化"排序。每层注明复用点、产出、护栏。

### L1 收口 — 证照真嵌入（建议先做）

- **做什么**：把"材料已备"从文字变成**真的把扫描件嵌进 docx**。
- **复用**：`ComplianceEvidenceBinding` → `EnterpriseMaterial` → MinIO 取文件；图片直接插入，PDF 用 `fitz` 渲染成页图插入。
- **产出**：`二、供应商资格证明资料`从占位变成加盖公章扫描件的真实材料页。
- **护栏**：仅嵌入 `confirmed` 且数据级别允许的材料；缺失项保留占位 + 待办。

### L2 — 评分索引引擎（最高差异化）

- **做什么**：解析评分办法 → 逐条评分点 → 自动生成"评分索引"表（评分点 → 本标书对应章节/附件/页码）→ 校验每个评分点是否有应答 + 证据，缺失当场标红。
- **复用**：`ComplianceItem(item_type=scoring)` 已抽出评分项；`compliance_generation` 的评分识别规则。
- **产出**：把 L2 覆盖从 `pending` 骨架升级为真实"已覆盖/缺应答"判定。
- **价值**：这是相对人工/通用 LLM **最难替代**的能力——"AI 帮你拿分/不丢分"。

### L3 — 偏离表 / 报价表逐条

- **做什么**：偏离表接技术参数逐条（招标条款 ↔ 我方响应，自动标"响应/偏离"）；报价表接工程量清单（逐项报价、算术校验、不超预算）。
- **复用**：`ComplianceItem(item_type=technical_response)`；招标技术/商务条款抽取。
- **护栏**：偏离判定需人确认；报价不臆造数字，缺则留空待填。

### L4 — 实质叙述（最后做，受事实约束）

- **做什么**：仅当项目确需技术方案/施工组织设计时，生成受事实约束的叙述骨架；后续再接 LLM 做风格润色。
- **护栏**：必须受 L1–L3 已确认事实约束，**不许编造证据/页码/指标**；当前装配器只输出已知事实、技术响应条款、评分点提示、报价校验结果与通用过程控制，不补造 DN、MPa、长度、管材型号、工程量或现场踏勘结论。

## 5. 合规护栏（贯穿所有层）

1. **不臆造**：拿不到事实/材料 → 留可见占位 `［待填:字段］` 或标 `needs_material`，绝不编。
2. **核心资格优先暴露**：营业执照/资质/信用等缺失标 `disqualifying`，在自检清单红牌置顶。
3. **可校验**：每个"要求"都有明确状态与缺口说明，人能一眼看到还差什么。
4. **建议 ≠ 生效**：覆盖判定与候选材料是建议，证据绑定/最终稿需人确认（与半自主编排一致）。
5. **来源可追溯**：嵌入的材料、引用的条款均来自检索命中的真实 material/chunk。

## 6. 当前进度小结

- ✅ 五模块装配管道贯通，仓顶招标文件可一键产出投标文件 docx。
- ✅ L1 合规覆盖完整 + 分层自检清单渲染 + 废标风险红牌。
- ✅ L2/L3 覆盖已接入数据层：评分点按证据绑定判定覆盖状态，技术响应条目进入偏离/响应表；未知应答、偏离结论和页码定位失败项保持可见缺口。
- ✅ L1 收口：已确认且数据级别允许的企业材料可从 MinIO 取出并嵌入 docx；缺失项仍保留占位/待办。
- ✅ L2：`ComplianceItem(item_type=scoring)` 已进入覆盖报告与评分索引表；有 active 证据绑定才判为已覆盖；评分索引页码列已改为 Word 原生 `PAGEREF` 域，指向实际章节/附件/材料书签，打开文档或更新域后按真实分页回填。
- ✅ L3：`technical_response` 条目已进入偏离/响应表；工程量/报价清单支持 Decimal 算术校验与预算/最高限价校验。
- ✅ 装配器与数据层（ComplianceItem/EvidenceBinding/EnterpriseMaterial）已完成正式接线。
- ✅ L4：技术方案/施工组织/服务承诺等章节已由人工占位升级为事实约束叙述骨架，审阅版保留待确认边界，正式版转为招标文件/施工图/工程量清单约束表达。
- ✅ 评分索引真实页码回填已接入：装配器不猜页码，改由 Word/LibreOffice 分页引擎更新书签引用；无法定位目标的评分项在审阅版显示待定位，正式版留空。

相关代码：`backend/app/services/tender_compliance_coverage.py`、`tender_format_assembler.py`、`tender_format_templates.py`；测试：`backend/tests/test_tender_compliance_coverage.py`、`test_tender_format_templates.py`。
