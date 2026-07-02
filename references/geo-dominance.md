# GEO Dominance — AI 搜索统治策略

GEO (Generative Engine Optimization) 不是 SEO 的附加品。到 2025 年，AI Overviews、ChatGPT、Perplexity、Bing Copilot 已经分走了 15-30% 的搜索流量。本文档是统一作战手册——把分散在各处的 GEO 信号整合成一个可执行的统治策略。

---

## 1. AI 搜索格局

| 平台 | 流量份额 | 引用机制 | 优化重点 |
|------|---------|---------|---------|
| **Google AI Overviews** | 最大（桌面+移动） | 从索引中提取，引用来源链接 | EEAT + 结构化数据 + answer-first + 品牌实体 |
| **ChatGPT (web search)** | 快速增长 | Bing 索引 + 实时搜索，内联引用 | llms.txt + 段落可摘引性 + 来源权威 |
| **Perplexity** | 中，技术/学术用户多 | 多源聚合，显示来源卡片 | 实体清晰 + 数据可验证 + 学术/行业来源 |
| **Bing Copilot** | 中等，企业用户多 | Bing 索引，侧重结构化信息 | Bing Webmaster Tools + 结构化数据 |
| **Claude (web search)** | 新兴 | 搜索后综合，偏好长篇权威内容 | 深度内容 + EEAT 信号 |

## 2. 统一 GEO 优化框架

按影响力从高到低排列。每一项都是「AI 引不引用你」的独立信号。

### Layer 1：可爬取性（没有这层，后面全是空气）

**llms.txt** — AI 爬虫的入口地图
- 路径：`/llms.txt`（根目录）
- 格式：https://llmstxt.org 标准 — H1 标题 + blockquote 摘要 + 分段链接列表含简短描述
- 生成方式：从页面/产品/分类数据源动态生成，不与 sitemap 不同步
- 各栈实现：见 `../vibio-fix/references/seo-fix-principles.md` 的 §11 和对应 stack adapter

**AI 爬虫访问控制**
- `robots.txt` 中**不要**屏蔽以下 User-Agent：
  - `Google-Extended`（Google AI Overviews 的数据源）
  - `GPTBot`（OpenAI/ChatGPT）
  - `CCBot`（Common Crawl，被多个 AI 引擎使用）
  - `anthropic-ai`（Claude）
  - `PerplexityBot`
- **除非你确实不想被 AI 引用**——有些内容（如付费内容、客户数据）需要屏蔽

**渲染可达性**
- AI 爬虫通常不执行 JavaScript
- 关键内容必须在服务端渲染的 HTML 中直接可见
- 测试：`curl https://example.com/page | grep "关键内容关键词"` → 必须有输出

### Layer 2：结构化数据（AI 的机器可读层）

AI 引擎解析 Schema.org 结构化数据来理解实体和关系。以下类型对 GEO 最重要：

| Schema 类型 | GEO 价值 | 必须字段 |
|------------|---------|---------|
| `Organization` | 品牌实体识别，Knowledge Graph 的基础 | `name`, `url`, `logo`, `sameAs` |
| `WebSite` | 站点名称在 AI 回答中的显示 | `name`, `url`, `potentialAction` (SearchAction) |
| `Article` / `BlogPosting` | 文章可被 AI 摘引的前提 | `headline`, `author`, `datePublished`, `dateModified`, `description` |
| `Product` | 产品信息被 AI 推荐引用 | `name`, `description`, `offers`, `brand` |
| `FAQPage` | FAQ 段落被 AI 直接提取回答 | `mainEntity` → 每个 Question + Answer |
| `HowTo` | 步骤被 AI 摘引为操作指南 | `step` 列表，每步含 `text` |
| `BreadcrumbList` | 帮助 AI 理解站点结构 | `itemListElement` |
| `Dataset` | 数据/统计被 AI 引用时带来源 | `name`, `description`, `creator`, `datePublished` |

**GEO 特有的 Schema 规则：**
- `Organization.sameAs` 必须包含所有官方平台的完整 URL（LinkedIn、Wikipedia、Wikidata、YouTube、行业数据库）
- `Article.author` 必须链到真实的 Author 页面（含作者资历），不是空壳
- `dateModified` 必须真实更新——AI 引擎会检查发布日期与内容时效是否一致

### Layer 3：可摘引性（AI 引不引你的核心）

**AI 摘引段落必须满足：脱离上下文也能独立成立。**

段落级可摘引性检查：
- [ ] 每个 H2 小节的第一句是否直接回答了该节的核心问题？
- [ ] 关键数据/结论是否在独立的 `<p>` 中，还是嵌在大段文字里？
- [ ] 是否避免了「如上所述」「前面提到」「见下文」等跨段依赖？
- [ ] 是否避免了 AI 可能误读的歧义表述（如「它」「这个」「前者」在脱离前文后指代不明）？

**段落结构模板（GEO 最优格式）：**
```html
<h2>什么是碳纤维预浸料？</h2>
<p>碳纤维预浸料（Carbon Fiber Prepreg）是将碳纤维织物预先浸渍树脂基体后制成的半固化片材，在航空航天和汽车工业中广泛用于制造轻量化结构件。</p>
<p>【展开详细说明...】</p>
```
第一句 = 40-60 字完整定义 → AI 可直接摘引为「什么是 X」的回答。

**结构化事实优先：**
AI 引擎更容易摘引结构化数据 → 对比表、规格表、步骤列表、FAQ。
- 规格对比 → `<table>`（不是 div 模拟的表格）
- 选型步骤 → `<ol>` 带完整句子
- 常见问题 → `<h3>` 问题 + `<p>` 答案 + FAQPage schema

### Layer 4：品牌实体信号（AI 认不认识你）

**品牌实体强度 = AI 引用你的概率。**

信号层级（从强到弱）：
1. **Wikipedia 条目** — 最强的实体确认信号。如果没有独立条目，至少确保在相关条目中被提及
2. **Wikidata 条目** — 即使没有 Wikipedia，Wikidata 也能建立实体
3. **Knowledge Graph 出现** — Google 搜索品牌名时出现 Knowledge Panel → 实体已建立
4. **权威媒体提及** — 被行业媒体、新闻网站、学术论文引用为来源
5. **行业数据库收录** — Crunchbase、LinkedIn Company Page、行业目录
6. **一致性 NAP** — Name/Address/Phone 在所有平台上完全一致
7. **sameAs 链接** — Organization schema 中列出所有官方平台 URL

**品牌实体检查清单：**
- [ ] 搜索 `"你的品牌名"` — AI Overviews 出现吗？Knowledge Panel 出现吗？
- [ ] 搜索 `"你的品牌名" + 核心产品` — 你是信息来源还是被忽略？
- [ ] Organization schema `sameAs` 是否包含 ≥ 5 个权威平台链接？
- [ ] 品牌名是否在行业 Wikipedia 条目中被提及（作为 reliable source）？
- [ ] 过去 12 个月内是否有 ≥ 2 次被权威媒体/行业报告引用？

### Layer 5：引用优化（让 AI 的引用链接指向你）

**当 AI 引用你时，确保最优质的页面被选中。**

引用页面优化：
- 被引用的页面必须在 1 秒内加载（AI 引擎有爬取超时）
- 被引用的段落必须不含付费墙/登录墙
- 页面 `canonical` 必须正确（AI 可能引用 canonical URL 而非实际 URL）
- 页面不应有大量广告/弹窗（AI 爬虫视为低质量信号）

**多源一致性：**
- 同一事实在文章内多个位置出现时，措辞一致
- 同一数据在不同平台（网站、LinkedIn、行业报告）的值一致
- 矛盾数据 → AI 降低对该来源的信任

---

## 3. 按平台定制

### Google AI Overviews
- **最关键信号：** EEAT + 结构化数据 + 段落可摘引性
- **触发 AI Overviews 的查询类型：** 信息型（"what is" / "how to" / "why does"）、对比型、定义型
- **引用偏好：** 偏好权威来源（政府/学术/知名品牌），其次是 EEAT 强的独立站点
- **特色：** AI Overviews 可能引用页面中的特定句子并附来源链接——这就是「answer-first 首句」的直接回报
- **工具：** `seo-google` → GSC 可以过滤 AI Overviews 的展示/点击数据

### ChatGPT (web search)
- **最关键信号：** llms.txt + Bing 索引 + 段落可摘引性 + 来源权威
- **引用偏好：** 偏好长篇、深度、有具体数据的内容；不太偏好纯商业页面
- **特色：** ChatGPT 会在回答中内联引用（如 `[1]`），点击展开来源卡片
- **工具：** Bing Webmaster Tools（ChatGPT 使用 Bing 索引）

### Perplexity
- **最关键信号：** 段落可摘引性 + 实体清晰 + 数据可验证
- **引用偏好：** 偏好有明确来源标注的数据；学术/技术来源权重高
- **特色：** 显示多个「Sources」卡片，用户可以选择只看某个来源的结果
- **策略：** 在文章内创建「自成一体的独立小节」，每个小节 = 一个 Perplexity 来源卡片

### Bing Copilot
- **最关键信号：** Bing 索引 + 结构化数据
- **工具：** Bing Webmaster Tools → IndexNow 协议 → 比 Google 更快收录

---

## 4. GEO 测量

### 应该追踪的 GEO KPI：
| 指标 | 数据来源 | 频率 |
|------|---------|------|
| AI Overviews 展示次数 | GSC（Search Appearance → AI Overviews） | 周 |
| AI Overviews 点击次数 | GSC | 周 |
| llms.txt 抓取频率 | 服务器日志 | 月 |
| 品牌在 ChatGPT/Perplexity 中的出现 | 手动抽查 | 月 |
| 品牌搜索量趋势 | GSC | 月 |
| Knowledge Panel 变更 | 手动 | 季度 |

### 品牌 GEO 可见性评分（0-100）：

```
GEO 分数 = 
  llms.txt 存在且更新 (20分) +
  所有 4 个 AI 爬虫未被屏蔽 (10分) +
  Organization + WebSite schema 完整含 sameAs (15分) +
  关键页面 answer-first 段落通过可摘引性检查 (20分) +
  ≥3 个权威来源引用品牌 (15分) +
  Wikipedia/Wikidata 条目存在 (10分) +
  GSC AI Overviews 数据存在 (10分)
```

| 分数 | 等级 |
|------|------|
| 80-100 | **AI 统治级** — AI 引擎视你为可靠信息来源 |
| 60-79 | **可被发现** — AI 有时引用你，但非首选 |
| 40-59 | **基本可见** — AI 知道你的存在，但缺少权威信号 |
| 20-39 | **隐形** — AI 基本不引用你 |
| 0-19 | **无 GEO** — 没有被 AI 发现的条件 |

---

## 5. GEO 执行路线图

### 第 1 周：可爬取性基线
- [ ] 创建/更新 llms.txt（从数据源动态生成）
- [ ] 检查 robots.txt 未屏蔽 AI crawlers
- [ ] 验证关键内容在无 JS 的 curl 中可读

### 第 2 周：结构化数据
- [ ] 完善 Organization schema（含 sameAs）
- [ ] 完善 WebSite schema
- [ ] 文章页加 Article schema（含 author + dateModified）
- [ ] 产品页加 Product schema
- [ ] FAQ 页加 FAQPage schema
- [ ] 所有 schema 通过 Rich Results Test 验证

### 第 3 周：可摘引性优化
- [ ] 重写关键页面的 H2 首句 → 40-60 字完整答案
- [ ] 消除「如上所述」「前面提到」等跨段依赖
- [ ] 关键数据从散文改为表格/列表
- [ ] 每个关键 H2 小节确保可独立摘引

### 第 4 周：品牌实体 + 测量
- [ ] 提交/更新 Wikidata 条目
- [ ] 整理所有权威媒体报道链接 → 加入 sameAs
- [ ] 建立 GEO KPI 追踪
- [ ] 首次品牌 GEO 评分
- [ ] 月度 GEO 可见性复查纳入 REVIEW 模式

---

## 6. 工具路由

| GEO 任务 | 工具 |
|----------|------|
| llms.txt 生成/验证 | 对应 stack adapter + curl 验证 |
| Schema 验证 | `seo-schema` |
| AI 爬虫可访问性 | curl + robots.txt 检查 |
| 段落可摘引性 | `seo-geo` |
| 品牌实体检查 | 手动搜索 + `seo-geo` |
| GSC AI Overviews 数据 | `seo-google` |
| 竞品 GEO 对比 | `seo-competitor-pages` + 手动检查竞品 llms.txt/schema |
