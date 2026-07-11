---
name: vibio-audit
description: >-
  当用户要求“SEO 审计/体检”“检查网站或 URL”“为什么没有收录、排名或询盘”“review my SEO”“technical SEO audit”时使用。本 Skill 对代码库或线上站点做有边界的证据审计：检查真实 HTTP 与渲染产物，核对最新官方规则，识别当前资源焦点和独立严重阻断，并按可验证影响、置信度、工作量和依赖关系排序。默认用中文报告；外部 seo-*、GSC、抓取和 SERP 能力均为可选，缺失时按 manifest 降级且绝不虚构数据。不用于单纯路线图、已知问题的直接修复或泛 SEO 概念问答。
compatibility: 代码库、URL 或导出数据均可作为输入。联网、Search Console、分析平台、SERP、抓取与第三方 SEO 能力均非必需；只有在实际可用时才调用。
---

# Vibio SEO AUDIT

默认用中文沟通和交付；目标市场中的搜索词、页面文案和 SERP 原文保留目标语言，并用中文解释。

审计的目标不是堆检查项，而是找出当前最可能限制有效自然搜索结果的资源焦点。先证明观察，再判断影响；所有独立的访问、索引、安全、人工处置或重大转化阻断都必须并行报告，不能因只选一个资源焦点而隐藏。官方建议不自动等于排名因素。

## 必读资料

开始前按需读取：

- `references/evidence-policy.md`：证据等级、数值论断和建议记录。
- `references/capability-routing.md`：能力选择、降级方案和不可知边界。
- `references/google-search-docs.md`：Google 当前规则；易变事项行动前重新核验实时官方页。
- `references/javascript-rendering.md`：HTTP 源码、静态构建、浏览器 DOM 的证据边界与 SPA 验证。
- `references/seo-fix-principles.md`：与技术栈无关的目标状态。
- `references/core-web-vitals.md`：有 CrUX/RUM/PSI/Lighthouse 输入时区分字段与实验室证据。
- `references/faceted-navigation.md`：目录、筛选、排序、分页或站内搜索形成参数空间时读取。
- `references/bing-webmaster-docs.md`：目标市场包含 Bing、IndexNow 或 Bing AI Performance 时读取。
- `references/stack-detection.md`：代码、渲染栈和编辑模式识别。
- `references/paid-search-intelligence.md`：仅在付费数据能回答 SEO 决策时使用。

## 自带确定性工具

当输入包含静态构建目录、浏览器导出 DOM，或允许对线上 URL 做有限抓取时，优先运行 `scripts/seo_inspect.py`，先生成 JSON 证据和中文 Markdown，再由本 Skill 判断业务影响。工具解析完整 HTML、JSON-LD、sitemap、robots 与范围内链接图；在静态构建模式还检查本地图片引用是否真实存在，不使用字符串 grep 或无来源健康分。报告必须保留 `evidence_mode=http_source|static_build|browser_dom`；只有 `--browser-provenance` 将每个 URL、DOM SHA-256、浏览器、采集时间和 JavaScript 状态校验通过时，才可写 `client_side_dom_verified=true`。

```bash
python scripts/seo_inspect.py \
  --site-dir dist --base-url https://example.com/ \
  --sitemap public/sitemap.xml --robots public/robots.txt \
  --json-out .vibio/runs/audit.json \
  --markdown-out .vibio/runs/audit.md
```

客户端站点另保存浏览器导出的 DOM；能取得初始源码时用同一路径布局配对：

```bash
python scripts/seo_inspect.py --rendered-dom .vibio/evidence/rendered \
  --source-input .vibio/evidence/source \
  --browser-provenance .vibio/evidence/browser-provenance.json \
  --base-url https://example.com/ \
  --json-out .vibio/runs/browser-dom.json --markdown-out .vibio/runs/browser-dom.md
```

线上模式使用 `--start-url` 和明确的 `--max-pages`，但内置有界 HTTP 抓取器不执行 JavaScript。它只连接经校验的公网目标、逐跳复验重定向、将 robots 自动发现的 sitemap 限于站点同源，并限制单响应字节数。浏览器不可用或未提供 DOM 时，把客户端 metadata、正文、canonical、结构化数据与链接写成“未经 JavaScript 渲染验证”，不能从源码断言其最终状态。只有用户确认输入代表生产目标站时才加 `--production`；静态构建或浏览器 DOM 文件都不能证明 HTTP。报告命中是调查证据，不自动等于排名原因；工具未覆盖内容质量、搜索意图、Google-selected canonical、真实收录或业务结果。

## 工作流

### 1. 明确范围与决策

1. 确认项目根、目标 URL/市场/语言、主要转化和用户真正要做的决定。
2. 如存在 `.vibio/`，先读取 `project.md`、相关 tracker 和近期 `changelog.md`，避免重复审查已验证或已修复事项。
3. 说明审计边界：全站、目录、模板组或单页；只有一个 URL 时不得推断已覆盖全站。
4. 列出当前可用的代码、渲染 HTML、sitemap、日志、GSC/GA4/CRM 导出和历史基线。

### 2. 选择证据与能力

先列出需要证据支持的决策，再检查提供商。`seo-audit`、`seo-page`、`seo-technical`、`seo-schema`、`seo-firecrawl`、`seo-google`、`seo-dataforseo` 等都只是 `vibio.manifest.yaml` 声明的可选能力。

- 能力可用：用它收集证据，再人工核对关键发现。
- 能力不可用：采用 `references/capability-routing.md` 中对应 fallback，继续做范围明确的源码、渲染产物、导出或人工样本检查。
- 数据仍不可得：明确写成“未知/未验证”，不得生成排名、流量、搜索量、难度、索引、外链或转化数字。

### 3. 检查真实产物

先保存工具命令、输入范围、失败 URL 与 JSON 报告；再按业务风险选择代表性页面类型，至少区分首页、列表/分类、详情/产品、内容和本地化模板中实际存在的类型。检查：

1. **搜索资格**：按 `references/javascript-rendering.md` 分开验证状态码/HTTP 源码与浏览器 DOM；检查 `noindex`、robots、登录墙、关键 JS、soft-404、History API、权限回退和可索引主内容。
2. **URL 信号**：重定向、canonical、sitemap、hreflang、参数 URL 和内部链接是否表达同一意图。
3. **意图与价值**：页面类型是否匹配当前目标市场 SERP，是否提供原创事实、专家经验或完成任务所需的信息。
4. **发现与架构**：重要页面是否可通过可抓取链接发现，是否存在孤儿页、重复所有权或规模化低价值页面。
5. **搜索展示资格**：title/snippet 的准确性，以及与可见内容一致、当前仍受支持的结构化数据。Schema 提供机器可读线索并可创造搜索功能资格，但不证明排名或生成式 AI 展示。
6. **体验与业务结果**：移动端关键任务、真实用户性能证据、表单/购买路径、测量覆盖和合格转化定义。
7. **AI 搜索**：先检查正常 Search 资格与非同质化价值。Google 不要求 `llms.txt`、特殊 AI Schema 或 AI 专用改写；不得将其缺失列为 Google 排名问题。

解析完整 JSON-LD 对象，不用字符串 grep 代替结构验证。抓取被 WAF/CDN 拒绝时可更换浏览器 UA 或来源，但要区分“工具未取到”与“搜索引擎无法访问”。代码库审计要尽量同时检查源码、构建结果和代表性浏览器 DOM。重要链接必须在相应证据层中表现为可解析的 `<a href>`；浏览器 DOM 快照之外的 console/network 异常与路由导航仍需单独验证。

### 4. 判定证据

每个发现分开记录观察与结论：

- E1 官方规则可证明资格、政策或产品行为，不能单独证明该项会提高排名。
- E2 第一方数据用于判断范围和业务影响。
- E3 受控实验只在已测试范围内支持因果结论。
- E4-E5 只能形成有边界的建议或实验假设。

标题和 meta description 不使用固定字符数闸门；FAQPage/HowTo 不作为 Google 富结果机会；Google Indexing API 不用于普通页面。普通 URL 的发现依赖可抓取链接、sitemap 和正常抓取资格。

### 5. 排优先级

严重程度表示潜在伤害，优先级综合：

```text
已验证影响 × 置信度 × 受影响范围
再结合工作量、依赖、可逆性与业务时效排序
```

只在已验证的访问/索引阻断、人工处置/垃圾政策风险、安全风险或重大业务故障时使用 `Critical`。缺少可选增强项或一条官方建议不构成 Critical。不要用无来源权重生成健康分。

### 6. 交付

先给出主导约束与审计覆盖，再用以下字段报告每项发现：

```text
Observation:
Affected scope:
Evidence level and source:
Verified on:
Business/search impact:
Confidence:
Priority and rationale:
Action:
Artifact verification:
Outcome metric and observation window:
Owner / dependency:
```

单独列出未覆盖范围、不可用数据、假设和误报风险。输出技术栈、渲染方式、SEO 所有者/插件、编辑模式及置信度，供 FIX 复用。

### 7. 闭环

- 用户授权实施时，将高置信度、可编辑发现继续交给 FIX；否则只交付诊断，不擅自改生产代码。
- 项目允许维护状态时，按 `references/state-templates.md` 把关键发现和待复盘指标写入 `.vibio/`。
- 广告数据只能验证目标市场查询、意图、信息表达、落地页和合格转化；广告支出绝不能作为自然排名因素，也不在审计中扩展为泛 Campaign 运营。

## 不要做

- 不把官方建议、相关性或 checklist 分数称为排名因素。
- 不把源码存在某标签等同于渲染正确、已抓取、已索引或已取得效果。
- 不把 GSC query 与 GA4/CRM 转化做确定性用户级连接。
- 不因外部 `seo-*` 能力缺失而停止，也不伪造其本应返回的数据。
- 不承诺固定 CTR、转化率、流量 uplift、排名或生效时间。
