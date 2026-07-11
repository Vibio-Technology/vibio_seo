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
- `references/seo-fix-principles.md`：技术栈无关的目标状态和验证协议。
- `references/stack-detection.md`：识别渲染层、SEO 所有者和编辑模式。
- `references/stack-adapters/`：已覆盖技术栈的落地方式；没有专用 adapter 时仍按目标规范实现。
- `references/capability-routing.md`：可选能力与降级方案。

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

按已验证影响、置信度、工作量、依赖和可逆性排序。优先修复真实访问/索引阻断、错误状态码、错误 canonical、渲染失败和测量故障；可选展示增强不能越过主瓶颈。

### 4. 实施最小改动

- 匹配项目现有代码、组件、插件和内容所有权。
- 修复 title/snippet 时追求准确、简洁、独特和意图一致，不使用固定字符数上限，也不保证 Google 采用提供文本。
- 只为可见、真实内容添加当前受支持的结构化数据。Schema 提供机器可读线索并可创造搜索功能资格，但不保证展示、排名或生成式 AI 展示。
- 不为 Google 富结果收益添加 `FAQPage` 或 `HowTo`；FAQ/步骤内容本身对用户有用时可保留。
- 不把 `llms.txt`、特殊 AI Schema、AI 专用改写或 `Google-Extended` 控制当作 Google Search 修复。只有目标平台有实时官方支持且用户明确需要时，才可把平台专属文件作为低风险可选项，并写清适用边界。
- 普通页面不使用 Google Indexing API；它仅支持符合条件的 `JobPosting` 和嵌套直播 `BroadcastEvent` 页面。
- 小且可逆的授权改动直接实施；涉及迁移、大规模 URL、canonical 系统或生产风险时，先给变更集、依赖和回滚方案。

外部 `seo-schema`、`seo-sitemap`、`seo-hreflang`、`seo-images`、`seo-performance` 等能力可用时用于加速验证；不可用时按 manifest fallback 使用解析器、构建、浏览器或人工检查，不得编造工具结果。

### 5. 验证产物

按风险执行项目现有的 build、lint、类型检查和测试，再检查代表性页面的：

1. 状态码、redirect chain、headers 与 robots 指令。
2. 渲染后的 title、description、canonical、hreflang、可抓取链接和主内容。
3. 解析后的 JSON-LD 对象及其与可见内容、当前功能要求的一致性。
4. sitemap/robots 中的真实 URL、canonical 一致性和协议格式。
5. 移动端关键任务、媒体 URL 与核心转化是否被改坏。

无法启动服务或发布时，明确标记“源码/构建已验证，线上渲染待验证”。不要把 lab 指标当作真实用户现场结果。

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
