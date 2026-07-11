---
name: vibio-fix
description: >-
  当用户要求“直接修 SEO”“改 canonical/robots/sitemap/hreflang”“加或修结构化数据”“修 title、meta、OG、索引或渲染问题”“implement SEO fixes”“fix technical SEO”，并希望修改代码、模板或 CMS 时使用。本 Skill 识别技术栈与编辑模式，按当前官方规则实施最小可验证改动，并在 HTTP 与渲染产物中复验。默认用中文沟通；外部 seo-* 能力全部可选，缺失时走 manifest fallback。不用于首次全站诊断、路线图、正文写作或泛广告运营。
compatibility: 有代码或模板权限时直接修改；仅有 URL/CMS 权限时交付精确 handoff 并在发布后复验。构建、浏览器、Schema、GSC 与第三方 SEO 能力按可用性使用。
---

# Vibio SEO FIX

默认用中文沟通和交付；面向目标市场的 title、description、可见文案和其他页面内容使用目标语言。

FIX 的完成标准不是“源码已改”，而是目标行为已在 HTTP、headers、渲染 HTML 或平台预览中验证。抓取、索引、排名和收入属于后续结果，不能由一次构建证明。

## 必读资料

- `references/evidence-policy.md`：证据和承诺边界。
- `references/google-search-docs.md`：当前 Google 资格与产品行为；易变事项实施前核验实时官方页。
- `references/javascript-rendering.md`：源码、静态构建与浏览器 DOM 的验证边界及 SPA 失败回退。
- `references/seo-fix-principles.md`：技术栈无关的目标状态和验证协议。
- `references/core-web-vitals.md`：性能修复涉及 LCP/INP/CLS 时区分字段证据与 lab 诊断。
- `references/faceted-navigation.md`：筛选、排序、分页、站内搜索或参数 URL 修复时读取。
- `references/bing-webmaster-docs.md`：实施 IndexNow 或面向 Bing 的修复时读取。
- `references/stack-detection.md`：识别渲染层、SEO 所有者和编辑模式。
- `references/stack-adapters/`：已覆盖技术栈的落地方式；没有专用 adapter 时仍按目标规范实现。
- `references/capability-routing.md`：可选能力与降级方案。

## 自带产物复验工具

对静态构建目录、浏览器导出的 DOM 或发布后的有限 HTTP 源码范围，使用 `scripts/seo_inspect.py` 保存机器可读的 before/after 报告。静态构建模式会把引用但不存在的站内图片列为 finding；恢复真实文件或移除无效引用后再复跑，不能只补 alt。先用同一 `--base-url`、证据模式、sitemap、robots 与范围跑基线，修复后以完全相同参数复跑；只比较与修复契约相关的 finding、页面字段和链接，不把 finding 总数下降称为 SEO 效果。

```bash
python scripts/seo_inspect.py --site-dir dist --base-url https://example.com/ \
  --sitemap dist/sitemap.xml --json-out .vibio/runs/after.json \
  --markdown-out .vibio/runs/after.md --fail-on high
```

`--site-dir` 只代表 `static_build`，不会执行 JavaScript；`--start-url` 只代表 `http_source`，内置有界 HTTP 抓取器也不会执行 JavaScript，并会拒绝非公网/混合 DNS、私网重定向、robots sitemap 跨源自动跟随和超限响应。客户端 JS 生成的 metadata、正文和链接必须用外部浏览器导出的 `--rendered-dom` 检查，并用 `--browser-provenance` 绑定 URL、DOM SHA-256、浏览器、采集时间和 JavaScript 状态后才标为已验证；能保存初始源码时再加 `--source-input` 检查初始 noindex、canonical 和客户端新增内容。`--fail-on` 仅作为产物闸门；退出成功不能证明已抓取、已索引、排名或收入增长。

## 工作流

### 1. 读取上下文

1. 确认项目根、目标页面/模板、目标市场和用户授权的修改范围。
2. 如存在 `.vibio/`，读取当前栈、近期变更、待修项和已约定的结果指标。
3. 从 AUDIT 接手时复用其观察证据、受影响范围和栈检测结果，不重复猜测。
4. 若问题尚未被验证，先做最小诊断；不要根据检查清单直接改代码。

### 2. 确定栈与所有权

按 `references/stack-detection.md` 输出：

```text
Stack / rendering:
Content source:
SEO owner or plugin:
Edit mode: code | template | CMS | URL-only
Selected adapter:
Evidence, confidence and unknowns:
```

先确认哪个层负责 title、canonical、Schema、robots 和 sitemap，避免框架、主题与插件重复输出。无法确认时走 URL-only handoff，不把站点硬套成某个框架。

### 3. 定义修复契约

对每个问题记录：

```text
Observed defect and evidence:
Target behavior:
Official requirement/recommendation:
Affected scope:
Files/templates/CMS fields:
Artifact verification:
Outcome metric and observation window:
Rollback condition:
```

把修复契约逐项映射到验证器：记录由 `seo_inspect.py` 的哪个 finding/字段、项目测试或哪条独立断言判定通过。若自带检查器不覆盖某项，就补一个范围明确的独立断言并保存输出；不能因为聚合 finding 为 0，就把未被验证的要求写成已通过。before 发现、实施决策、after 证据和最终状态必须能逐项闭环。

按已验证影响、置信度、工作量、依赖和可逆性排序。优先修复真实访问/索引阻断、错误状态码、错误 canonical、渲染失败和测量故障；可选展示增强不能越过主瓶颈。

### 4. 实施最小改动

- 匹配项目现有代码、组件、插件和内容所有权。
- 修复 title/snippet 时追求准确、简洁、独特和意图一致，不使用固定字符数上限，也不保证 Google 采用提供文本。
- 只为可见、真实内容添加当前受支持的结构化数据。Schema 提供机器可读线索并可创造搜索功能资格，但不保证展示、排名或生成式 AI 展示。
- 不为 Google 富结果收益添加 `FAQPage` 或 `HowTo`；FAQ/步骤内容本身对用户有用时可保留。
- 不把 `llms.txt`、特殊 AI Schema、AI 专用改写或 `Google-Extended` 控制当作 Google Search 修复。只有目标平台有实时官方支持且用户明确需要时，才可把平台专属文件作为低风险可选项，并写清适用边界。
- 普通页面不使用 Google Indexing API；它仅支持符合条件的 `JobPosting` 和嵌套直播 `BroadcastEvent` 页面。
- 图片引用在构建或发布范围内缺失时，先核对 public/static 目录、构建管道、CDN/重写和真实生产请求。能够定位已有真实素材时恢复原文件；装饰性引用无素材时移除无效标记和布局占位；实质性产品图没有获批素材时移除破图引用并记录媒体缺口，等待业务方提供。不要生成占位文件、猜测看不到的图片内容或仅补 `alt` 后判通过；只有看过真实图片与页面语境后才写描述性 alt，纯装饰图使用 `alt=""`。
- 小且可逆的授权改动直接实施；涉及迁移、大规模 URL、canonical 系统或生产风险时，先给变更集、依赖和回滚方案。

外部 `seo-schema`、`seo-sitemap`、`seo-hreflang`、`seo-images`、`seo-performance` 等能力可用时用于加速验证；不可用时按 manifest fallback 使用解析器、构建、浏览器或人工检查，不得编造工具结果。

### 5. 验证产物

按风险执行项目现有的 build、lint、类型检查和测试，再用相同范围运行 `scripts/seo_inspect.py` 并检查代表性页面的：

1. 状态码、redirect chain、headers 与 robots 指令。
2. 渲染后的 title、description、canonical、hreflang、可抓取链接和主内容。
3. 解析后的 JSON-LD 对象及其与可见内容、当前功能要求的一致性。
4. sitemap/robots 中的真实 URL、canonical 一致性和协议格式。
5. 移动端关键任务、媒体 URL 与核心转化是否被改坏。

SPA/客户端路由还要按 `references/javascript-rendering.md` 测试真实 HTTP deep link、未知路由 soft-404、History API 刷新/前进后退、初始 noindex、canonical 所有者、`<a href>`、匿名权限/API 回退和 console/network 异常。浏览器不可用时把这些项标为未验证，不能用 `urllib` 或静态构建结果代替。

无法启动服务或发布时，明确标记“源码/构建已验证，线上渲染待验证”。不要把 lab 指标当作真实用户现场结果。

需要交付 `reproduce.sh` 或同类独立复现实物时，固定实际运行的检查器版本与 SHA-256。优先把该版本只读复制到证据目录，或让脚本通过显式环境变量定位并在执行前校验摘要；不要把临时工作区的绝对 Skill 路径写死成唯一入口。复现脚本必须分别断言 before/after JSON 的 `tool` 和 `version` 等于预期值，再校验实际脚本 SHA-256；只固定摘要不算完成版本校验。脚本还要对修复契约的关键字段和资源存在性作断言，而不只是复跑检查器并接受退出码。

### 6. 交付与复盘

交付内容包括：变更文件/平台位置、关键 diff、运行的验证、通过/失败/未验证项、风险与回滚、需要观察的页面级搜索/业务指标。

Search Console URL Inspection 或少量关键 URL 的 request indexing 可用于诊断和请求重新抓取，但不保证收录，也不能替代可发现性、sitemap、内链与页面价值。观察窗口应依据实际抓取、数据量、站点历史和销售周期设定，不使用固定生效周数。

任务允许维护状态时，按 `references/state-templates.md` 将已实施变更、产物验证、结果指标、复盘日期和回滚条件追加到 `.vibio/changelog.md`。

## 下一步路由

| 结果 | 下一步 |
|---|---|
| 产物验证失败或发生回归 | 留在 FIX，修复后重新验证 |
| 产物通过、等待搜索效果 | 转 REVIEW，按预设窗口和对照复盘 |
| 修复暴露出新的未知范围 | 转 AUDIT，做有边界的根因诊断 |
| 剩余事项需要依赖与产能排序 | 转 PLAN，更新执行路线图 |

## 不要做

- 不声称 build 成功等于已收录、已排名或已带来转化。
- 不添加重复 metadata/Schema 所有者，也不覆盖用户未授权的生产配置。
- 不用固定 title/meta 长度、CTR、转化率或 uplift 作为完成标准。
- 不把广告设置或预算优化混入技术修复；付费数据只能作为 SEO 查询、落地页和转化情报。
- 不因外部能力缺失而虚构验证结果。
