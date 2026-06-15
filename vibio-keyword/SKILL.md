---
name: vibio-keyword
description: |
  当用户说「我的产品该做哪些关键词」「帮我做关键词研究 / 关键词调研」「这个业务该针对什么词做 SEO」「找一批高意图关键词」「关键词该怎么分组 / 哪些值得做」「竞品在做哪些词」「帮我搭关键词架构」时，应使用本 skill。
  企业产品/业务 → 扩展种子词 → 路由 seo-dataforseo 拉真实搜索量/难度/意图 → 按搜索意图分类、按可操作性打分 → 关键词族映射到页面（已有/新建/合并/降级）→ 划 3-5 个主题簇 → 写进 .vibio/trackers/keywords.md。面向 B2B/外贸默认走 b2b-seo 的买家旅程视角。
  不应触发：要的是整体 90 天计划（用 vibio-plan，它会在关键词阶段调用本 skill 的方法）、审查现有页面问题（用 vibio-audit）、直接改代码（用 vibio-fix）、单页内容大纲（用 seo-content-brief）。
  Use when the user wants keyword research / keyword strategy for a product or business: which keywords to target, how to group them by intent, what's worth doing. Expands seeds, pulls real volume/difficulty via seo-dataforseo, sorts by intent, maps to pages, writes the keyword tracker.
---

# Vibio SEO — KEYWORD 引擎

回答一个具体问题：**这个企业的产品/业务，该针对哪些关键词做 SEO 才有效果？** 不是拍脑袋列词，是从真实搜索数据 + 意图 + 可操作性出发，给出"主攻哪些词、怎么分组、各归到哪个页"的可落地关键词架构。

核心约束：**关键词要绑定真实搜索数据和意图，绑定到具体页面；不堆没人搜的词，不追打不过的大词。**

---

## 执行流程

0. **读项目记忆。** 开工前用 `Read` 读项目根 `.vibio/`（格式见 `vibio-memory`）：已有 `trackers/keywords.md` 就在它基础上扩充/复核，别重头再来；`project.md` 里的业务模型、目标市场、栈也直接复用。

1. **理解业务，提种子词。** 从产品/业务、真实站点（有 URL/代码就读现有页面和现有 title）、用户描述里提 10-15 个种子主题。B2B 制造/外贸尤其要分清：
   - **产品词**（buyers 搜的料/规格：carbon fiber fabric、fiberglass mat 3mm…）
   - **应用/场景词**（按行业：carbon fiber for wind turbine blades…）
   - **商业意图词**（manufacturer / supplier / wholesale / custom…）
   - **信息词**（what is / vs / how to choose…买家教育）

2. **扩展候选集。** 把 10-15 种子扩到 50-300 候选。路由 `seo-dataforseo`（实时搜索量/难度/意图/相关词/趋势，需 MCP）；可用时用它拉真实数据，不可用就**明确说明数据缺失**，退回基于 SERP 观察 + 业务判断的定性估计，别编数字。竞品在做的词路由 `seo-dataforseo` 的竞品分析或 `seo-competitor-pages`。

3. **按搜索意图分类。** 每个词标意图：`商业/交易`（要买/找供应商）、`信息`（学习/对比）、`导航`（找特定品牌）。B2B 用 `b2b-seo` 的买家旅程视角分层（认知→评估→决策）。**Vibio 默认偏向商业意图 + 应用场景词**——外贸 B2B 的钱在"找供应商"和"特定应用选材"上，不在泛信息流量。

4. **按可操作性打分。** 每个候选词问四件事（来自 operating-system 的 SOP）：
   - **相关性** — 真和业务/产品相关吗？
   - **能不能答** — 站点能为它提供真正有价值的页面吗？
   - **SERP 打不打得过** — 难度 vs 站点当前权重，现实吗？（低权重新站别拿高难度大词开局）
   - **值不值得单建页** — 够不够撑起一个独立页面？
   留下"相关 + 能答 + 打得过 + 值得做"的，砍掉其余。

5. **关键词→页面映射。** 一个关键词族对应**一个**主页面，标记：`已有页面`（优化它）/ `新建` / `合并`（多页抢同词→自相蚕食，合并）/ `降级`。暴露 cannibalization（站内多页竞争同一词，互相拖累）。

6. **划主题簇。** 把关键词族组织成 3-5 个 hub-and-spoke 主题簇（一个商业 hub 页 + 若干支撑信息页内链上去）。深度做需要按真实 SERP 重叠分簇时，路由 `seo-cluster`。

7. **写回记忆 + 交付。** 用 `Write`/`Edit` 把结果写进 `.vibio/trackers/keywords.md`（词/意图/归属页/优先级/难度/当前排名/趋势，字段见 `vibio-memory` 的 state-templates），并在 `project.md` 标注关键词架构已就绪。输出给用户：主攻词表（按优先级）+ 意图分组 + 页面映射 + 簇结构 + 下一步。

---

## 该路由哪些专家

- `seo-dataforseo` — **真实搜索量/难度/意图/趋势/竞品词**（回答"哪个词值得做"的硬数据来源；需 MCP）
- `b2b-seo` — B2B/外贸关键词研究 + 买家旅程内容分层（Vibio 默认）
- `seo-cluster` — 按真实 SERP 重叠做主题簇（不是文本相似度）
- `seo-competitor-pages` — 竞品在排的词、对比/替代页机会
- `seo-content-brief` — 选定关键词后，单页的内容大纲（含字数）——这是 keyword 的下游，不在本 skill 内做

数据类专家需要 MCP/API。不可用时如实说明，给定性版本，别编搜索量。

---

## 下一步路由（关键词架构定了之后）

| 触发条件 | 推荐 |
|---------|------|
| 关键词和页面映射已定，要把它排进执行节奏 | 「关键词架构已就绪并写进 `.vibio/`。跑 `vibio-plan` 把它接进 90 天路线图（先做哪些页、什么节奏）。」 |
| 某个目标词要开始写页面 | 「这个词要落地成页面，跑 `seo-content-brief` 出带字数的内容大纲，再交给写作/`vibio-fix` 落地。」 |
| 发现现有页面有自相蚕食 | 「站内多页在抢同一个词。建议跑 `vibio-audit` 确认范围，再 `vibio-fix` 做合并/重定向。」 |
| 没有 dataforseo 数据、用户想要真实量 | 「真实搜索量需要 DataForSEO MCP（或 GSC 已有数据用 `seo-google`）。现在给的是定性估计，接上数据源后能精确化。」 |

---

## 不要做

- 不编造搜索量/难度数字——没有真实数据就标"估计"并说明来源。
- 不给一长串没分意图、没绑页面、没排优先级的"关键词清单"——那不是架构。
- 不替低权重新站推荐高难度大词作为开局。
- 不为单个长尾词建独立页（值不值得单建页是打分项之一）。
- 不做单页内容大纲（那是 `seo-content-brief`），本 skill 只到"词→页映射 + 簇"为止。
- 不跳过读 `.vibio/` 就重做一份已经存在的关键词表。
