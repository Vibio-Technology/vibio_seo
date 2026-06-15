---
name: vibio-audit
description: |
  当用户说「审查我的站」「审查这个项目的 SEO」「检查这个页面 / 这个 URL」「为什么这个页面排不上去」「review 一下我的 SEO」「做个全站 SEO 体检」，或直接丢一个网址让你看看 SEO 怎么样时，应使用本 skill。栈无关：输入可以是任意语言/框架的代码库，也可以只是一个 URL（直接访问抓取页面结构、meta、JSON-LD、robots、sitemap）。
  读真实产物 → 识别站点用什么栈搭建 → 对照 Google 官方文档（技术要求/结构化数据/垃圾政策/helpful content）判定 → 路由到对应 seo-* 专家工具并行分析 → 对抗式验证发现 → 按 Critical/High/Medium/Low 优先级排序、每条引到官方 URL → 用 Write/Edit 写回 .vibio/ 记忆（格式见 vibio-memory）→ 能修的带着栈信息转交 vibio-fix。开工前先用 Read 读项目记忆，续上次而非重审。
  不应触发：要的是执行计划/路线图（用 vibio-plan）、已知问题直接改代码（用 vibio-fix）、纯概念问答。区分 vibio-review：本 skill 做「首次/现状诊断」（找问题）；「之前改过、想看见效没」的复测用 vibio-review。
  Use when the user wants to audit a site or codebase (any stack), check a page, diagnose why something won't rank, or just hands over a URL. Inspects the real artifact, detects the stack, routes to specialist seo-* skills, returns prioritized findings.
---

# Vibio SEO — AUDIT 引擎

你不是凭印象点评，你是核实证据，而且以 Google 官方文档为准绳。读真实产物，对照官方规则，路由到专家工具，给出按优先级排序、可追溯到官方的发现，能修的立刻转 `vibio-fix`，剩下的作为有范围的任务交回。

---

## 执行流程

0. **读项目记忆。** 开工前先用 `Read` 直接读项目根的 `.vibio/`（格式约定见 `vibio-memory`）：有记忆就续上次（已知栈、上次主瓶颈、已修项、待办），别重审已解决的；没有就是新项目，照常往下走，收工时用 `Write` 建记忆。

1. **读真实产物（两种入口对等）。**
   - **只有一个 URL** → 这是主路径之一。直接访问抓取：路由到 `seo-page`（单页深挖）/ `seo-audit`（全站）/ `seo-firecrawl`（全站抓取/建图）/ `seo-technical`，必要时用 `WebFetch`/`curl` 兜底。抓出渲染后的 title/meta/canonical/robots meta/JSON-LD/OG/标题层级/图片/hreflang/sitemap/llms.txt 的真实状态。
   - **有代码库** → 读 SEO 配置（metadata、JSON-LD、robots、sitemap、layout/模板的 `<head>`），看构建/头部配置，抽样几个页面文件。先跑 `references/seo-fix-principles.md` 的目标规格当清单，分钟级抓出高频缺口，再决定要不要上重型抓取。

2. **识别栈。** 用 `references/stack-detection.md` 判断站点用什么搭建（Next.js / WordPress / Shopify / 静态站 / 未知）以及能不能改代码。这一步的产出要**带给 `vibio-fix`**，让它不必重新识别——输出一句话：「栈：X，编辑模式：改代码/改模板/CMS 粘贴。」

3. **路由到专家。** 把每个关注点对应到 `references/skill-arsenal.md` 里的某个 sub-skill 并调用，独立的并行跑。全站审计常见扇出：`seo-technical` + `seo-schema` + `seo-content` + `seo-sitemap` + `seo-geo` + `seo-images`。规则：**先路由，后综合**，不要手搓专家已经做得好的分析。

4. **对照官方文档判定。** 审查基准是 `references/google-search-docs.md`（Google 技术要求、结构化数据、垃圾政策、helpful content/E-E-A-T），不是 best-practice 民间说法。每条发现要能引到具体官方页。**混合用法**：常见情况用蒸馏好的规则（快、可追溯）；遇到新功能、要求存疑、或用户质疑时，WebFetch 对应官方 URL 核实当前措辞再下结论（Google 会更新政策）。

5. **对抗式验证。** 不报告你没在真实渲染 HTML / 源码里确认过的问题。明确说你检查了什么、没检查什么。三条实战铁律（都来自真实误报教训）：
   - **跨层级抽样，别只看一个页就推全站。** 站点常有多种页型（首页 / 品类页 / 叶子产品页 / 应用页 / blog），schema 和 meta 在不同层级差异很大——只抓品类页会误判"产品页缺 Product schema"，实际叶子页齐全。每种页型至少抓一个代表。
   - **完整解析 JSON-LD，别用 grep 扫 @type 就下结论。** 结构化数据常嵌套（`Organization` 里裹 `ContactPoint`/`PostalAddress`/`geo`），简单 grep 会漏掉外层类型导致"无 Organization"式误报。把 `<script type="application/ld+json">` 块解析成对象再看顶层 @type。
   - **抓不到先换 UA，再下"抓取失败"结论。** `WebFetch` 常被 WAF/CDN 返 403；改用 `curl -sL -A "<浏览器 UA>"` 几乎都能拿到真实渲染 HTML。别把 403 当成"页面有问题"。

6. **排优先级。** `Critical`（违反技术要求/命中垃圾政策——见 google-search-docs §1/§3）> `High`（明确影响排名）> `Medium`（优化项）> `Low`（锦上添花）。先确认有没有可索引性阻断（误加 noindex、robots 封禁、非 200、错 canonical），那永远是第一位。每条发现按 `google-search-docs.md` 末尾的「what / rule+URL / severity / fix」格式给出。

7. **写回记忆 + 转交。** 用 `Edit` 把发现追加到 `.vibio/changelog.md`（带日期、优先级、引用的官方 URL、是否已修），用 `Write`/`Edit` 更新 `project.md` 的栈/状态。可立即修的小改动带着栈信息直接进 `vibio-fix`；较大的列成有范围的任务交回用户。

---

## 专家工具库（27 个 seo-* 的调度地图）

完整能力、触发时机、依赖见 `references/skill-arsenal.md`。快速速查：

| 需求 | 路由到 |
|---|---|
| 全站审计 / 健康分 | `seo-audit`，或任意站点用 `seo` |
| 单页深挖 | `seo-page` |
| 技术（抓取/索引/CWV/robots/JS 渲染）| `seo-technical` |
| Schema / 结构化数据 / 富结果 | `seo-schema` |
| Sitemap 分析或生成 | `seo-sitemap` |
| 内容质量 / E-E-A-T / 薄内容 | `seo-content` |
| 内容大纲（含字数）| `seo-content-brief` |
| 主题簇（SERP 重叠）| `seo-cluster` |
| 批量/程序化页面 | `seo-programmatic` |
| 对比 / 替代页 | `seo-competitor-pages` |
| AI Overviews / ChatGPT / Perplexity / llms.txt | `seo-geo`、`seo-flow` |
| 好页面为什么不排名（SERP 倒推）| `seo-sxo` |
| 外链 / 引用域 / 毒链 | `seo-backlinks` |
| 实时 SERP / 搜索量 / 难度（MCP）| `seo-dataforseo` |
| GSC / GA4 / CrUX / PageSpeed / Indexing API | `seo-google` |
| 全站抓取 / 死链（MCP）| `seo-firecrawl` |
| hreflang / 国际化 | `seo-hreflang` |
| 图片 alt/尺寸/格式/CLS | `seo-images`；生成 OG/hero 图 → `seo-image-gen` |
| 本地 / GBP / NAP / 地图 | `seo-local`、`seo-maps` |
| 电商 / Shopping / 市场 | `seo-ecommerce` |
| SEO 回归 / 基线对比 | `seo-drift` |

如果某个 sub-skill 需要的 MCP/API 不可用，说明情况并回退到源码级检查。

---

## 常见诊断路径

- **全站审计（线上 URL）** → `seo-audit`（内部自行扇出），或并行 `seo-technical` + `seo-schema` + `seo-content` + `seo-sitemap` + `seo-geo`。
- **代码库 SEO 审查（任意栈）** → 先用 `references/seo-fix-principles.md` 的目标规格过一遍，识别栈，再 `seo-schema` 校验 JSON-LD、`seo-technical` 查抓取/索引逻辑。
- **「没流量 / 排不上去」** → `seo-google`（到底有没有被索引？）→ `seo-sxo`（意图/页型错配？）→ `seo-content`（深度/E-E-A-T？）。
- **AI 搜索可见性** → `seo-geo` + `vibio-fix` 的 `llms.txt` 配方。

---

## 下一步路由（审查完成后）

| 触发条件 | 推荐 |
|---------|------|
| 发现可直接修的问题（OG 图、缺 schema、缺内链等）| 「已定位 N 个可修问题。栈是 X，跑 `vibio-fix` 直接改（有代码就改代码/模板，托管平台就给可粘贴片段），改完在渲染产物里验证。」 |
| 问题多且需要排期，而非即时修 | 「现状已诊断清楚。建议跑 `vibio-plan` 把这些发现排进 90 天路线图。」 |
| 审查确认是意图/页型错配 | 「这是页型与搜索意图错配，不是技术问题。已用 `seo-sxo` 定位，改稿方向见发现项。」 |
| 记忆里有过往改动、想知道之前改的有没有见效 | 「`.vibio/` 里有历史改动。想看见效情况就跑 `vibio-review` 复测（GSC + 基线对比）。」 |

---

## Reference 文件

- `references/google-search-docs.md` — **审查基准**：Google 官方技术要求、结构化数据、垃圾政策、helpful content/E-E-A-T，每条带官方 URL。混合用法：常见情况用蒸馏规则，存疑/新功能时 WebFetch 官方页核实。
- `references/skill-arsenal.md` — 27 个 `seo-*` 专家的能力地图与调度规则。

栈识别用 `references/stack-detection.md`，目标规格用 `references/seo-fix-principles.md`（两者是 `vibio-fix` 同源文件的同步副本，审查阶段够用；真正落地修复在 `vibio-fix`）。记忆用 `Read`/`Write` 直接读写项目根 `.vibio/`，格式见 `vibio-memory`。

---

## 不要做

- 不报告没在真实源码/HTML 里确认过的问题。
- 不给引不到 Google 官方规则的「best practice」式发现——结论要能追溯到 `google-search-docs.md` 的某条 + URL。
- 不把原始专家输出直接转述，要整合进按优先级排序的结论。
- 不在没看真实产物前就下判断。
- 不只抓一个页 / 只用 grep 扫就给全站结论——跨页型抽样、完整解析 JSON-LD（见对抗式验证三铁律）。
- 不跳过读记忆就重审一个已经诊断过的项目。
