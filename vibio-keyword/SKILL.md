---
name: vibio-keyword
description: |
  当用户问产品该做哪些关键词、目标市场买家是否真的这样搜、哪些词值得做、如何分组或映射页面、竞品覆盖什么查询时使用。流程从 RFQ/CRM/GSC/付费 search terms 等真实买家语言出发，结合目标国家与语言的 SERP 和口径明确的需求数据，验证母语表达、受众/页型、地区需求、搜索者身份与商业路径，再完成词族到页面映射、cannibalization 检查和任务簇，写回 keyword tracker。Use for evidence-led target-market keyword research, validation, intent grouping, and page mapping.
  不应触发：整体路线图（`vibio-plan`）、现有页面审计（`vibio-audit`）、代码修复（`vibio-fix`）或只要单页大纲（`seo-content-brief`）。
---

# Vibio SEO — KEYWORD 引擎

本引擎交付的不是一串“有量的词”，而是**目标市场中经证据验证、各自有主页面和业务路径的查询族架构**。搜索量、KD 和意图标签都有工具口径与不确定性；不能把第三方估算叫 Google 的真实数据。

## 执行流程

### 0. 续接项目状态

读取项目根 `.vibio/`；已有 `trackers/keywords.md` 就增量复核，复用 `project.md` 的业务、市场、语言与主转化。无记忆则创建最小项目上下文。具体文件操作使用当前环境可用的读写能力，不绑定某个客户端工具名。

### 1. 建种子任务

从产品目录、服务、现有页面、RFQ/CRM、销售异议和用户输入提取种子。B2B 常见任务包括产品/规格、应用、供应商/采购、标准/认证、选型/对比和售后排错。种子数量由业务范围决定，不为达到固定配额补词。

### 2. 扩展候选

按 `references/keyword-validation.md` 的买家语言顺序扩展：一方 RFQ/CRM/站内搜索 → GSC → paid search terms → 目标市场原生来源 → SERP/Autocomplete/相关问题 → 第三方工具。

`seo-dataforseo` 可用时，用目标国家、语言、设备和日期获取其供应商口径下的搜索量、趋势、SERP 与难度估算；`seo-google` 可用时优先用自有 GSC。能力不可用就走 reference 的降级链，并标明 `unverified` 或 `conditional`，绝不编数字。

### 3. 判断意图和买家任务

为词族记录：目标角色、要完成的任务、商业/信息/导航/本地等意图、买家旅程位置及合理下一步。优先级由合格需求、企业可服务性、商业价值与信息增益决定，不由“抗零点击”或固定流量折扣决定。

### 4. 目标市场验证

全量候选执行 `references/keyword-validation.md` 五道闸门：

1. 目标市场原生/买家表达是否支持；
2. 目标地区 SERP 的人群、任务和页型是否匹配；
3. 需求与趋势证据是否匹配国家/语言口径；
4. 搜索者身份是否与客户相符；
5. 是否有真实商业路径且企业能兑现承诺。

标 `pass / conditional / fail`。单条 PAA、商业结果或 RFQ 可以支持“保留待验证”，但不自动证明整体搜索需求。工具 0 量走零量框架，不直接淘汰，也不直接采信。

### 5. 决定投资顺序

对通过或条件通过的词族逐项记录：

- **商业价值**：对合格线索、订单或销售效率的作用；
- **需求证据**：哪些一方/目标市场数据支持；
- **意图与页型**：计划页面是否符合当前 SERP；
- **信息增益**：企业能提供哪些独有规格、案例、数据、工具或经验；
- **当前立足点**：已有页面、查询、内链、品牌或引用证据；
- **成本/依赖/可测性**。

按 `references/authority-cascade.md` 标 `now / next / later / reject`。第三方 KD 只是带工具、市场和日期的辅助竞争信号，不再用 `cascade_phase: 1-4`。

### 6. 词族到页面映射

一个买家任务/查询族指定一个主页面，标记：`existing / new / merge / expand / reject`。发现多个 URL 在相同查询与意图中轮换时，记录 cannibalization 证据并给合并、区分或 canonical/重定向的后续动作。

同义词和轻微修饰词合入同页；只有任务、页型、产品能力或市场确有差异才拆 URL。

### 7. 形成任务网络

将共同完成买家任务的页面连接成商业页、规格/应用、选型/对比、案例/证据和支持内容网络。Query fan-out 只用于发现相关问题面，不作为批量建页词表。需要真实 SERP 重叠数据时可路由 `seo-cluster`；不可用时依据任务和有限 SERP 证据定性分组。

### 8. 写回与交付

更新 `.vibio/trackers/keywords.md`，至少包含词族、市场/语言、买家/任务、意图、验证、主页面、`now/next/later/reject`、数据来源、趋势和决策理由。保留历史，不覆盖旧快照。

交付：优先查询族 + 验证证据 + 页面映射 + cannibalization + 任务网络 + 数据限制 + 下一步。

## 专家能力与降级

- `references/keyword-validation.md`：五道验证闸门与降级链；
- `references/paid-search-intelligence.md`：用 Keyword Planner、search terms、paid & organic report 与合格线索学习服务 SEO；
- `seo-dataforseo`：第三方口径的地区需求、SERP、趋势、竞品与难度数据；
- `seo-google`：自有 GSC 查询/页面数据；
- `seo-sxo`：深读 SERP 意图和页型；
- `seo-cluster`：按可观察 SERP 重叠辅助分簇；
- `seo-competitor-pages`：拆竞争页面的任务与缺口；
- `seo-content-brief`：为已选页面做大纲；`vibio-content`：把验证后的页面任务写成证据充分的成稿。

所有 `seo-*` 都是可选能力。缺失时按 manifest fallback 和 reference 的公开/一方证据流程执行，并声明限制。

## 下一步路由

| 条件 | 下一步 |
|---|---|
| 架构已定，需要排执行 | `vibio-plan` 按容量和依赖排路线图 |
| 某个页面开始生产 | 需要大纲则 `seo-content-brief`，随后 `vibio-content` 写成稿，再由 `vibio-fix` 上线 |
| 发现 cannibalization | `vibio-audit` 确认范围，`vibio-fix` 落地合并/区分/重定向 |
| 数据源不足 | 交付缺口与最短验证实验，不承诺接上某工具就“精确” |

## 不要做

- 不编搜索量、KD、排名周期或商业结果；所有数值保留来源、市场、日期和限制。
- 不把全球量、Ads CPC/competition 或第三方 KD 当目标国自然需求/难度真值。
- 不拿直译或其他出口商的循环措辞作为唯一证据。
- 不把工具 0 量直接淘汰或采信。
- 不用“打得过”“必胜”代替可观察的 SERP 缺口、站内立足点和信息增益。
- 不给同义词、单个超长尾或 fan-out 变体机械建页。
- 不交付没有验证、页面归属、优先级和证据限制的关键词清单。
- 不跳过 `.vibio/` 重做已有架构，也不覆盖历史数据。
