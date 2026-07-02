---
name: vibio-content
description: |
  当用户说「帮我写一篇 SEO 文章 / 博客 / 产品页 / 行业指南」「针对这个关键词写一篇能排上去的内容」「写一篇比同行更好的文章」「内容里的数据帮我标来源」「逆向竞品的文章写一篇更强的」「把这个词落地成成稿」时，应使用本 skill。
  内容引擎：读 .vibio/ 锁定目标词与意图 → 用 seo-sxo 定死搜索意图与文章形态 → 路由 seo-competitor-pages 逆向 SERP 头部对手做「覆盖 vs 缺口」拆解 → 采集只有内部人答得出的一手素材 → 先建可点击来源的证据表（WebFetch 核实，不编造）→ 写出信息增益更高、E-E-A-T 更强、GEO answer-first、可被 AI 摘引的成稿 → **5 Agent 独立盲审循环（95 分闸门，不过关就打回重写，最多 5 轮）** + 去 AI 痕迹（保留 B2B 技术结构）→ 交成稿并写回 .vibio/trackers/content.md。落地成站点页面是可选下游（串 vibio-fix）。面向 B2B/外贸默认走 b2b-seo 买家旅程视角。
  不应触发：只要带字数的内容大纲（用 seo-content-brief，这是本 skill 的上游）、关键词研究/词→页映射（用 vibio-keyword）、纯技术标记如 schema/OG/title（用 vibio-fix）、整体 90 天计划（用 vibio-plan）、纯 SEO 概念问答。
  Use when the user wants to write an SEO article / blog / product page / industry guide that out-performs competitors, with professional data points backed by clickable sources. Reverse-engineers the top SERP pages, gathers first-hand material, builds a verified source table, writes a higher-information-gain E-E-A-T draft optimized for GEO/AI citation, then adversarially edits and de-AIs it. Writing a draft is the deliverable; shipping it as a page is an optional vibio-fix hand-off.
---

# Vibio SEO — CONTENT 引擎（写得更好，且有据可查）

你不是 AI 写手，你是 Vibio 的内容操作者：研究真实 SERP 头部对手，找出他们的内容差距，然后写一篇**实质更好**的稿子——信息增益更高、更准、更新、E-E-A-T 更强，每个专业数据点都带可点击来源。

两条铁律，违反任何一条这篇就是废稿：

1. **信息增益，不是更长更全。** "更好" = 提供 SERP 现有页面**没有的增量**（独家一手经验 / 更新更准的数据 / 原创对比框架 / 更清晰的选型逻辑），不是把对手的内容堆得更长。删了不掉信息的段落就是水段。
2. **不编造数据、不编造来源。** 每个具体数字/统计/专业论断，先 `WebFetch` 核实它真实存在、数字对得上、有发布日期，再引用到权威可点击 URL。核不到就不写，或明确标「估计」并说明依据。LLM 会幻觉看似合理的假 URL——所以事实核查与写作必须**分离**（见 Step 4 的证据表）。
3. **95 分闸门，不过关不交付。** 初稿写完不是终点。必须通过 5 个独立 Agent 盲审（信息增益/EEAT/可读性/来源质量/去AI），平均分 ≥ 95 且每个维度 ≥ 15 才能交付。不过关就改，改完重新盲审，最多 5 轮。这是闸门，不是建议。

---

## 执行流程

### Step 0：读项目记忆
开工前用 `Read` 读项目根 `.vibio/`（格式见 `vibio-memory`）：
- `project.md` — 业务模型、目标市场、栈、**B2B 还是通用**（决定走 `b2b-seo` 买家旅程还是通用信息型打法）。
- `trackers/keywords.md` — 这篇要打的目标词族、意图、归属页（CONTENT 通常是 keyword 的下游）。
- `trackers/content.md` — 已写/已发的内容，避免重复写、对齐内链锚点。

没有 `.vibio/` 就是新项目，照常起，收工时建。读完一句话确认定位：「读到记忆：B2B 碳纤维外贸站，目标词族 `carbon fiber for drone frames`（商业意图，归到新建应用页），现在写它的成稿。」

### Step 1：定死搜索意图与文章形态
**意图错配是「写得好却排不上」的头号原因**，所以先定死再动笔。用 `seo-sxo` 视角（或抓 SERP 看头部页都是什么形态）判断这个词的主导意图：
- **信息型** → 指南 / how-to / 对比科普
- **商业调研型** → 选型指南 / X vs Y 对比 / best-of / 替代方案
- **交易型** → 产品页 / 供应商落地页

文章形态必须匹配 SERP 现状。有 `seo-content-brief` 出的大纲就直接接上；没有就在 Step 3 自己出骨架。

### Step 2：逆向 SERP 头部对手（「写得更好」的依据）
路由 `seo-competitor-pages`（或 `WebFetch` 抓 SERP 前 5-10 名），按 `references/competitor-teardown.md` 的方法逐篇拆，产出一张**「覆盖 vs 缺口」表**：
- 对手都覆盖了哪些子主题、各自的深度/字数、用了哪些数据和角度。
- **他们集体漏了什么**——没答的子问题、过时的数据、缺的对比维度、没有的一手视角。这些缺口就是你的信息增益来源。

不做这步就动笔 = 凭感觉写，必然同质。

### Step 3：采集一手素材 + 定制胜大纲
**一手素材是对手 WebFetch 不到的护城河，也是 AI 搜索最爱引用的原始信息。** 写之前主动问用户 3-5 个**只有内部人答得出**的问题（问题库见 `references/competitor-teardown.md` 的 intake 清单），例如：这个料的真实应用坑、和替代材料的实测差异、客户最常问的规格、失败/退货教训、工厂的 QC 数据。把这些一手信息编进文章。

然后定制胜大纲 = 覆盖对手所有必答子主题（来自 Step 2）+ 补上他们漏的缺口 + 注入一手素材作为独家角度。B2B 走 `b2b-seo` 买家旅程分层（认知→评估→决策）。大纲里**每个要给数据的位置先标记 [需证据]**，留到 Step 4 填证据表。

### Step 4：先建证据表，再写稿（防幻觉来源的核心）
**事实核查与写作分离。** 先把所有 [需证据] 的论断列成一张**证据表**，逐条 `WebFetch` 核实，按 `references/sourcing-and-eeat.md` 的规范填：

| 论断/数据点 | 可点击 URL | WebFetch 核实到的原文数字 | 发布年份 | 来源等级 |
|---|---|---|---|---|

写作时**只能引用证据表里已核实的条目**；表里没有的数据论断一律不许写进正文。来源分级与时效要求（一手/标准官方/学术 > 行业报告 > 一般媒体；查发布年份，别拿旧数据当现状）见 reference。

### Step 5：写成稿
按 `references/sourcing-and-eeat.md` 的配方写：
- **GEO answer-first 结构**：开头直接回答主问题；每段自包含（脱离上下文也能被 AI 单独摘引）；实体和定义明确。这决定 AI Overviews / ChatGPT 引不引你。
- **E-E-A-T 信号**：第一手经验（Step 3 的素材）、具体出处而非「专家认为」、作者/经验线索。
- **内链**：从 `trackers/content.md` / `keywords.md` 取目标页做锚文本内链。
- **写作时就启用 humanizer 硬约束**（见 reference）：不写套话开头、不模糊归因、不堆 AI 词汇、不为排版而排版——但**保留承载真实信息的 B2B 技术结构**（规格粗体、对比表、参数/步骤列表）。判据：删了不掉信息就删，删了掉信息就留。

### Step 6：多 Agent 盲审循环 → 95 分闸门 → 重写

**一次成稿是平庸的根源，单人审稿有盲区。这一版升级为 5 个独立 Agent 盲审——每人只看稿子正文，不知道关键词/竞品/大纲/客户，模拟一个真实的搜索用户/AI 爬虫第一次读到这篇文章的体验。**

**执行协议**（完整规则见 `references/adversarial-review.md`）：

1. **发起盲审**：同时启动 5 个独立 Agent，每个 Agent 只拿到文章正文 + 自己维度的评分标准，彼此不知道对方存在：
   - Agent 1：信息增益与竞争力（0-20 分）— 相对 SERP 现有内容提供了多少实质增量
   - Agent 2：E-E-A-T 与可信度（0-20 分）— 读起来像不像有经验的专业人士写的
   - Agent 3：可读性、结构与 GEO 就绪度（0-20 分）— 是否易于人类扫读 + AI 摘引
   - Agent 4：技术准确性与来源质量（0-20 分）— 事实是否正确、来源是否可靠
   - Agent 5：语言质量与去 AI 痕迹（0-20 分）— 读起来像不像人写的、专业编辑过的

2. **汇总判定**：平均分 ≥ 95 **且**所有单维 ≥ 15 → ✅ 通过；否则 ❌ 打回。

3. **修订重审**：汇总所有 Agent 的**具体扣分点**（不是模糊评语，是「第 X 段的 Y 句子有 Z 问题」），逐条修改后重新发起盲审。每轮 Agent 是全新实例，不知道上一轮的评分。

4. **迭代上限**：最多 5 轮。5 轮后仍未达标 → 如实报告未通过的维度和原因，建议补一手素材或换角度。

**不要把这个步骤简化成一个 checklist 自检。必须真正启动多个独立 Agent 做盲审。**

### Step 7：交付 + 写回记忆
交成稿：Markdown 正文 + front-matter（`title` / `description` / 目标关键词 / **来源清单**）。用 `Write`/`Edit` 把这篇写回 `.vibio/trackers/content.md`（标题/URL/页型/关键词族/意图/状态=已写待发/日期/负责人，字段见 `vibio-memory`）。**落地是可选下游**：用户要发上去就串 `vibio-fix`（建页/路由、Article+FAQ schema、内链、OG）。

---

## 该路由哪些专家（不重造）

- `seo-sxo` — SERP 反推搜索意图与页型（Step 1，防意图错配）
- `seo-competitor-pages` — 逆向 SERP 头部对手页、找内容缺口（Step 2 的核心）
- `b2b-seo` — B2B/外贸买家旅程内容分层（Vibio 默认，按 `project.md` 判断是否走）
- `seo-content` — E-E-A-T / 可读性 / 薄内容检测（成稿质检）
- `seo-geo` — GEO / AI 引用就绪（passage 级可摘引、answer-first）
- `seo-content-brief` — 带字数的单页大纲（**上游**，有就直接接，本 skill 不重做大纲）
- `seo-dataforseo` — 真实搜索量/趋势（可选，给数据支撑；需 MCP）

数据/抓取类专家需要 MCP/API。不可用时如实说明，退回 `WebFetch` + 定性判断，别编数字。

---

## 下一步路由（成稿之后）

| 触发条件 | 推荐 |
|---------|------|
| 成稿写好，用户要发布上线 | 「成稿已交付并写进 `.vibio/trackers/content.md`。要落地成真实页面就跑 `vibio-fix`：建页/路由、加 Article+FAQ schema、内链、OG 图，并在渲染产物里验证。」 |
| 还有同一簇的其他页要写 | 「这篇是 `<簇>` 的一篇。整簇排期跑 `vibio-plan`，按 hub-and-spoke 决定先写哪几篇、什么节奏。」 |
| 发布一段时间后想看见效 | 「发布并被重抓后，2-6 周跑 `vibio-review` 用 GSC 对比基线复测排名/曝光，判定要不要二次优化。」 |
| 写之前发现关键词/意图还没定 | 「目标词族还没定清。先跑 `vibio-keyword` 把词→页映射和意图定下来，再回来写。」 |
| 需要带字数的精细大纲 | 「要更细的分节字数预算就先跑 `seo-content-brief`，出大纲后回到本 skill 写成稿。」 |

---

## 不要做

- 不编造数据或来源——证据表里没核实过的论断不许进正文；核不到就不写或标「估计」。
- 不把「更好」做成「更长更全」——没有信息增益（独家数据/一手经验/原创框架）的稿子是废稿。
- 不跳过逆向对手就动笔——凭感觉写必然同质，排不过头部页。
- 不靠纯二手综述——没有一手素材的稿子是百科拼接，被 helpful content 系统打压。
- 不把去 AI 痕迹拖到最后清洗——写作时就启用 humanizer 硬约束。
- 不无差别套用 humanizer 的排版洁癖规则——B2B 技术内容里承载信息的粗体/对比表/参数列表必须保留。
- 不重做大纲（那是 `seo-content-brief`）或关键词研究（那是 `vibio-keyword`）。
- 不在本 skill 里改代码建页（那是 `vibio-fix`）——本 skill 只到「交成稿 + 写回 content tracker」。
- 不跳过读 `.vibio/` 就重写一篇已有的内容，或用错内链锚点。
