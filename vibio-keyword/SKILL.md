---
name: vibio-keyword
description: |
  当用户说「我的产品该做哪些关键词」「帮我做关键词研究 / 关键词调研」「这个业务该针对什么词做 SEO」「找一批高意图关键词」「这个词老外真的会搜吗 / 验证一下这些关键词」「目标市场用什么词搜我们产品」「关键词该怎么分组 / 哪些值得做」「竞品在做哪些词」「帮我搭关键词架构」时，应使用本 skill。
  企业产品/业务 → 扩展种子词（买家真实语料优先）→ 路由 seo-dataforseo 拉真实搜索量/难度/意图 → 按搜索意图分类 → **过目标市场验证五道闸门（母语性/SERP 试金石/目标国量/身份排除/商业路径，防直译陷阱）** → 按可操作性打分 + 标级联阶段 → 关键词族映射到页面（已有/新建/合并/降级）→ 划 3-5 个主题簇 → 写进 .vibio/trackers/keywords.md。面向 B2B/外贸默认走 b2b-seo 的买家旅程视角。
  不应触发：要的是整体 90 天计划（用 vibio-plan，它会在关键词阶段调用本 skill 的方法）、审查现有页面问题（用 vibio-audit）、直接改代码（用 vibio-fix）、单页内容大纲（用 seo-content-brief）。
  Use when the user wants keyword research / keyword strategy for a product or business: which keywords to target, whether target-market buyers actually search them, how to group them by intent, what's worth doing. Expands seeds from real buyer language, pulls real volume/difficulty via seo-dataforseo, validates every candidate against target-market search behavior (native-language evidence, SERP litmus test, per-country volume, searcher-identity filters), sorts by intent, maps to pages, writes the keyword tracker.
---

# Vibio SEO — KEYWORD 引擎

回答一个具体问题：**这个企业的产品/业务，该针对哪些关键词做 SEO 才有效果？** 不是拍脑袋列词，是从真实搜索数据 + 意图 + 可操作性出发，给出"主攻哪些词、怎么分组、各归到哪个页"的可落地关键词架构。

核心约束：**关键词要绑定真实搜索数据和意图，通过目标市场验证（目标国家的真实买家确实这么搜），绑定到具体页面；不堆没人搜的词，不追打不过的大词，不做直译出来的假词。**

---

## 执行流程

0. **读项目记忆。** 开工前用 `Read` 读项目根 `.vibio/`（格式见 `vibio-memory`）：已有 `trackers/keywords.md` 就在它基础上扩充/复核，别重头再来；`project.md` 里的业务模型、目标市场、栈也直接复用。

1. **理解业务，提种子词。** 从产品/业务、真实站点（有 URL/代码就读现有页面和现有 title）、用户描述里提 10-15 个种子主题。B2B 制造/外贸尤其要分清：
   - **产品词**（buyers 搜的料/规格：carbon fiber fabric、fiberglass mat 3mm…）
   - **应用/场景词**（按行业：carbon fiber for wind turbine blades…）
   - **商业意图词**（manufacturer / supplier / wholesale / custom…）
   - **信息词**（what is / vs / how to choose…买家教育）

2. **扩展候选集。** 把 10-15 种子扩到 50-300 候选。扩展来源优先走买家真实语料（`references/keyword-validation.md` 第三节工具箱：询盘/RFQ 原文 > GSC 查询 > 母语竞品页 > Autocomplete/PAA > Reddit/论坛 > B2B 平台联想）。路由 `seo-dataforseo`（实时搜索量/难度/意图/相关词/趋势，需 MCP；分国家用 `location_code`）；不可用就**明确说明数据缺失**，退回免费数据降级链（GSC → Autocomplete → Trends → Keyword Planner 区间），别编数字。竞品在做的词路由 `seo-dataforseo` 的竞品分析或 `seo-competitor-pages`。

3. **按搜索意图分类。** 每个词标意图：`商业/交易`（要买/找供应商）、`信息`（学习/对比）、`导航`（找特定品牌）。B2B 用 `b2b-seo` 的买家旅程视角分层（认知→评估→决策）。**Vibio 默认偏向商业意图 + 应用场景词**——外贸 B2B 的钱在"找供应商"和"特定应用选材"上，不在泛信息流量；且商业/规格词相对抗 AI Overview 零点击侵蚀。

4. **目标市场真实性验证（强制闸门）。** 全量候选过 `references/keyword-validation.md` 的五道闸门：①**母语性**（措辞在目标国母语来源里真实出现过——本土竞品/SERP/Autocomplete/论坛，防直译陷阱，不拿其他中国出口商站当证据）②**SERP 试金石**（目标国 locale 搜一遍，前 10 名的人群 = 你的客户；消费者博客/招聘站/词典主导即淘汰）③**量与趋势按目标国口径**（不看全球量；US/UK/AU 拼写与用词变体分别查）④**搜索者身份排除**（jobs/salary/DIY/how to make/free 等信号词命中即扣）⑤**商业路径**（搜的人到询盘还差几步）。每词标 `pass`/`conditional`/`fail`；fail 淘汰记录原因，conditional 只随长尾聚合投产。工具 0 量的规格/标准/牌号词走零搜索量判定框架（GSC 曝光/PAA 出现/SERP 有商业页/询盘原话，任一即采信），别直接扔。

5. **按可操作性打分。** 每个通过验证的词问四件事（来自 operating-system 的 SOP）：
   - **相关性** — 真和业务/产品相关吗？
   - **能不能答** — 站点能为它提供真正有价值的页面吗？
   - **SERP 打不打得过** — 难度 vs 站点当前权重，现实吗？（低权重新站别拿高难度大词开局）
   - **值不值得单建页** — 够不够撑起一个独立页面？
   留下"相关 + 能答 + 打得过 + 值得做"的，砍掉其余。同时标 `cascade_phase: 1-4`（KD 分级排序，见主库 `references/authority-cascade.md`），决定进 90 天路线图的哪一阶段。

6. **关键词→页面映射。** 一个关键词族对应**一个**主页面，标记：`已有页面`（优化它）/ `新建` / `合并`（多页抢同词→自相蚕食，合并）/ `降级`。暴露 cannibalization（站内多页竞争同一词，互相拖累）。

7. **划主题簇。** 把关键词族组织成 3-5 个 hub-and-spoke 主题簇（一个商业 hub 页 + 若干支撑信息页内链上去）。AI 搜索时代簇比单词更重要：覆盖主词 + fan-out 子问题面的页面被 AI 引用概率显著更高。深度做需要按真实 SERP 重叠分簇时，路由 `seo-cluster`。

8. **写回记忆 + 交付。** 用 `Write`/`Edit` 把结果写进 `.vibio/trackers/keywords.md`（词/意图/**验证标记**/归属页/优先级/难度/**级联阶段**/当前排名/趋势，字段见 `vibio-memory` 的 state-templates），并在 `project.md` 标注关键词架构已就绪。输出给用户：主攻词表（按优先级）+ 意图分组 + 验证结论 + 页面映射 + 簇结构 + 下一步。

---

## 该路由哪些专家

- `references/keyword-validation.md` — **目标市场真实性验证协议**（五道闸门/买家用语挖掘工具箱/US-UK-AU 地区变体/零量词判定/免费数据降级链）——Step 2 和 Step 4 的执行依据，动手前先 Read
- `seo-dataforseo` — **真实搜索量/难度/意图/趋势/竞品词**（回答"哪个词值得做"的硬数据来源；需 MCP；分国家查量用 `location_code`）
- `seo-google` — GSC 查询挖掘（已被 Google 验证的真实查询，零量词的第一采信证据）
- `seo-sxo` — SERP 页型深读（验证闸门②拿不准时的深度工具）
- `b2b-seo` — B2B/外贸关键词研究 + 买家旅程内容分层（Vibio 默认）
- `seo-cluster` — 按真实 SERP 重叠做主题簇（不是文本相似度）
- `seo-competitor-pages` — 竞品在排的词、对比/替代页机会
- `seo-content-brief` — 选定关键词后，单页的内容大纲（含字数）——这是 keyword 的下游，不在本 skill 内做

数据类专家需要 MCP/API。不可用时如实说明，按 `references/keyword-validation.md` 第七节降级链给定性版本，别编搜索量。

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
- 不跳过目标市场验证闸门——直译词、SERP 人群错配词、身份排除命中词，量再大也不进架构。
- 不拿中文词直译当外语关键词，不拿其他中国出口商站点当用词证据（循环引用 Chinglish）。
- 不看全球量做目标国决策——量按目标国家口径查；US/UK/AU 变体分别验证。
- 不把工具 0 量的规格/标准词直接淘汰——先走零搜索量判定框架。
- 不给一长串没分意图、没绑页面、没排优先级的"关键词清单"——那不是架构。
- 不替低权重新站推荐高难度大词作为开局。
- 不为单个长尾词建独立页（值不值得单建页是打分项之一）。
- 不做单页内容大纲（那是 `seo-content-brief`），本 skill 只到"词→页映射 + 簇"为止。
- 不跳过读 `.vibio/` 就重做一份已经存在的关键词表。
