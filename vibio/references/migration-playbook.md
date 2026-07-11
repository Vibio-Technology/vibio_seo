# SEO 迁移执行手册

域名、平台、URL、协议、渲染、信息架构或多语言结构的变化都可能改变搜索系统发现、抓取、规范化和理解页面的方式。迁移的目标是保存仍有效的用户任务与搜索资产，并让每个变更都可验证；不存在通用流量跌幅、恢复周期或“正常损失”。

## 一、定义范围与成功条件

先建立迁移简报：

```text
Migration type and business reason:
Old/new hosts, platforms and URL rules:
Target countries/languages and launch sequence:
In-scope templates, assets, feeds and subdomains:
Content/intent changes included:
Primary conversion and business guardrails:
Search baseline and comparable cohort:
Freeze date / launch owner / rollback authority:
Known constraints and irreversible steps:
```

尽量把主机/平台迁移与内容重写、导航重构、品牌改名等变量拆开或分批。必须同时进行时，保存每层前后规格并降低因果结论的置信度。

## 二、迁移资产台账

URL 清单应合并以下来源并去重：现有 sitemap、站内抓取、CMS/路由导出、GSC 页面数据、自然落地页、服务器日志、feed、PDF/图片/视频、hreflang、canonical、已核验外链和重要广告/邮件落地页。

每个旧 URL 记录：

| 字段 | 含义 |
|---|---|
| Old URL / canonical / status | 当前真实状态与规范信号 |
| Page task / market / locale | 用户任务、国家/语言和页型 |
| Search evidence | 页面/查询/国家/设备及日期范围 |
| Business evidence | 合格自然访问、转化、销售管道或保留义务 |
| Internal/external dependencies | 内链、hreflang、feed、引荐和已核验来源 |
| Disposition | keep、move、merge、retire、blocked-for-review |
| New URL / response | 目标 URL 或计划 404/410，及 301/308/200 |
| Owner / QA / rollback | 负责人、验证状态和恢复办法 |

外部数据缺失时仍可建立范围明确的清单，但要标注可能遗漏的孤儿 URL；不得把一次抓取称为全站完整库存。

## 三、URL 处置规则

1. **等价移动**：旧 URL 服务的主要任务在新站完整保留，使用服务端 301 或 308 直接指向最终新 URL。
2. **真正合并**：多个旧页被一个页面完整承接时，先迁移独特且有效的内容，再分别永久重定向到该页。
3. **任务消失且无替代**：返回 404 或 410。不要批量跳首页、分类页或无关商业页。
4. **暂不能判断**：标记 `blocked-for-review`，不让自动相似度映射直接上线。
5. URL 规范化规则应覆盖协议、主机、大小写、尾斜杠、参数和国际化路径，但先用真实样本测试冲突。
6. 图片、PDF、视频及其他仍有用户/搜索/引荐价值的资源也需要处置，不能只映射 HTML。
7. 重定向尽量一步到最终目标；上线前检测链、环、目标 4xx/5xx、批量 soft 404 和规则误命中。

“最接近页面”只有在能满足原主要任务时才是相关替代。页面内容、语言或地区不同，不能仅因 URL 字符相似就合并。

## 四、新站上线前闸门

### 技术与渲染

- 生产候选页返回预期状态，主内容在搜索引擎可处理的渲染结果中存在；
- staging 的认证、robots 或 `noindex` 控制不会泄漏到生产；
- canonical、hreflang、分页/分面、移动端和 JS 渲染与新 URL 规则一致；
- robots.txt 不阻断必要资源或目标内容，sitemap 只包含计划中的规范 URL 并使用准确 `lastmod`；
- title、主标题、meta robots、结构化数据、媒体和分析标记迁移完整；
- 导航、正文和相关页面中的内部链接直接指向新 URL；
- 错误页返回真实 4xx，服务器容量、缓存和 CDN 不产生间歇性错误。

### 市场与业务

- 每个目标语言/地区的内容、货币、库存、联系方式、法律要求和主转化可用；
- hreflang 返回互相一致的可索引页面，不与 canonical 冲突；
- 表单、电话、结账、CRM 来源和自然落地页测量通过端到端测试；
- 页面任务没有在模板迁移中被削弱，关键证据和信任要素仍可见。

### 映射测试

全量自动校验 redirect map，并按页型、市场、规则和业务风险分层人工抽样。抽样数量由总体规模、规则复杂度和可接受遗漏风险决定，不能用固定 URL 数宣称迁移已安全。

## 五、发布编排

1. 冻结旧站 URL、内容和模板变更，保存抓取、配置、数据库/静态产物和测量基线。
2. 预演 DNS、证书、CDN、重定向、缓存清除和回滚步骤；明确哪些变化不可快速逆转。
3. 上线后立即进行合成探测和分层抽样：核心入口 200、旧 URL 处置、robots、sitemap、canonical、hreflang、渲染与转化。
4. 提交准确的新 sitemap。普通页面依靠可抓取内链和 sitemap 被发现，不批量请求重新编入索引。
5. Google Indexing API 只用于当前支持的 `JobPosting` 或嵌套直播 `BroadcastEvent` 页面，不作为迁移提交工具。
6. 若为符合条件的域名迁移，在所有权和重定向验证后按 Google 当前文档使用 Search Console Change of Address；它不能替代重定向。
7. 保持旧域名、证书和永久重定向可用，并定期检查仍有流量/抓取/引荐的旧 URL。Google 对站点迁移的当前建议是重定向通常至少保留一年，并从用户角度尽可能长期保留；一年不是自动拆除日期，仍有用户、链接、抓取或业务依赖时继续保留。

## 六、监控与处置

监控频率由风险和数据成熟度决定：发布初期关注实时技术故障，搜索结果在抓取和报告数据成熟后复盘。不要用固定天/周/月作为成功判据。

### 领先信号

- 生产可用性、5xx、延迟、robots 和渲染错误；
- 旧 URL 的状态与重定向目标，链/环/soft 404；
- 新旧 sitemap、抓取日志、URL Inspection 与 Google-selected canonical；
- hreflang、资源、结构化数据和移动/桌面模板漂移；
- 分析与 CRM 事件完整性。

### 搜索与业务结果

- 按页面/查询/国家/设备/品牌拆分 GSC，不用全站平均排名下结论；
- 以旧 URL 与新 URL 的映射 cohort 合并比较，避免只看新页而漏掉旧页损失；
- 对齐同季节窗口或可比未迁移页面/市场，并记录同期发布、改版和需求变化；
- 在自然落地页、市场和时间 cohort 层面检查合格转化、销售管道和收入，不做查询到转化的确定性连接。

每个异常记录 `observation → affected scope → evidence → likely mechanism → owner → action → artifact verification → next signal`。未抓取或数据未成熟标 `not-yet-observable`，不可用“迁移本来就会跌”掩盖实现错误。

## 七、回滚边界

在发布前定义触发条件：核心页面不可用、广泛阻断抓取/索引、重定向系统性错误、关键市场或转化失效、测量损坏。回滚先恢复用户和技术资格，再保留故障证据。

域名变更、已广泛抓取的新 URL 和用户数据迁移未必能无代价回滚。对此应采用分批发布、流量切换、feature flag、双重验证和变更冻结来降低风险；不要把“可以回滚”写成未经演练的保证。

## 八、可选能力与降级

| 需要 | 可选能力 | fallback |
|---|---|---|
| 全站抓取/差异 | `seo-firecrawl`、`seo-drift` | sitemap + CMS/路由导出；用 curl/浏览器做风险分层抽样并保存快照 |
| GSC/URL Inspection | `seo-google` | 请求导出并在 GSC 界面核验关键样本；不可得时不声称索引结果 |
| 外链资产 | `seo-backlinks` | 使用用户导出、分析引荐和人工核验来源页 |
| 结构化数据 | `seo-schema` | 解析 JSON-LD，并对照最新官方功能文档和可用验证工具 |
| SERP | `seo-dataforseo` | 在目标市场做带日期的有限人工抽样，明确非穷尽 |
| 业务测量 | GA4/CRM | 先定义事件和所需导出；没有数据时只评估实施与搜索领先信号 |

能力不可用时缩小验证范围，不能虚构抓取、索引、排名、外链或业务结果。

## 九、官方参考与交付

- 站点迁移总览：https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes
- 更换主机：https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes
- 重定向：https://developers.google.com/search/docs/crawling-indexing/301-redirects
- 大型站点迁移管理：https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes#large-site
- Change of Address：https://support.google.com/webmasters/answer/9370220
- Indexing API 范围：https://developers.google.com/search/apis/indexing-api/v3/using-api

交付物包括：迁移简报、完整度说明、URL disposition/redirect map、上线闸门结果、部署与回滚 runbook、异常 tracker、搜索与业务基线、复盘设计。所有变更追加写入 `.vibio/changelog.md`，保留旧值与核验日期。
