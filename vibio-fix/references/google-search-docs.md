# Google 搜索官方基线

最后核验：2026-07-11。若实时官方文档与本缓存冲突，以实时官方文档为准。

使用本文件将各项主张路由到当前来源。引用实际观察到的产物，并标注准确的官方 URL；不要把建议表述为普遍适用的排名因素。

文档根目录：https://developers.google.com/search/docs

## 证据等级

- `官方要求`：资格条件、政策或有文档记录的产品行为。
- `官方建议`：有用的指导，但不构成保证。
- `第一方观察`：目标网站的 GSC、分析工具、日志或 SERP 证据。
- `实验`：已明确适用范围的因果测试。
- `假设`：采用前需要先衡量验证。

## 技术资格

来源：https://developers.google.com/search/docs/essentials/technical

Google 列出三项最低技术要求：Googlebot 未被屏蔽、页面返回成功的 HTTP 状态码、页面包含可索引内容。满足这些要求并不保证页面会被抓取、索引、取得排名或获得展示。

相关来源：

- 可抓取链接：https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- JavaScript SEO：https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Robots meta：https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag
- 规范化：https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- 站点地图：https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
- 分面导航：https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation

优先审计意外设置的 `noindex`、被屏蔽的资源/内容、误导性状态码、渲染失败、重复 URL 系统、损坏的可抓取链接和 canonical 冲突。

自引用 canonical 是建议，并非普遍适用的硬性要求。错误的 canonical 可能导致目标页面无法被选为规范页面，其风险高于缺少自引用 canonical。

Google Indexing API 不是通用提交工具。它只适用于包含 `JobPosting` 的页面，或包含嵌套在 `VideoObject` 中的直播 `BroadcastEvent` 的页面：https://developers.google.com/search/apis/indexing-api/v3/using-api

## 标题与摘要

- 标题链接：https://developers.google.com/search/docs/appearance/title-link
- 摘要/meta description：https://developers.google.com/search/docs/appearance/snippet

Google 没有规定固定的标题或 meta description 字符数上限；展示内容会按需截断，且通常受设备宽度影响。应编写简洁、描述准确、彼此不同且能代表页面的文本。不要依据僵化的 `50-60` 或 `150-160` 字符阈值进行审计，也不要承诺 Google 一定会采用所提供的文本。

## 结构化数据

- 功能库：https://developers.google.com/search/docs/appearance/structured-data/search-gallery
- 通用政策：https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- Organization：https://developers.google.com/search/docs/appearance/structured-data/organization
- 站点名称/WebSite：https://developers.google.com/search/docs/appearance/site-names
- Product：https://developers.google.com/search/docs/appearance/structured-data/product

结构化数据为 Google 提供理解页面的机器可读线索，并可使页面获得受支持搜索功能的资格；它不保证功能展示、排名或生成式 AI 展示。标记必须与可见内容一致，并满足该功能当前的必需/建议属性。应依据最新功能文档和 Rich Results Test 进行验证。

应按照当前文档的建议放置 Organization 和 WebSite/站点名称标记，通常放在首页，而不是要求全站每个页面都添加这两种标记。仅在用例真实且当前受支持时，才使用页面类型标记。

Google 已于 2026-05-07 停止展示 FAQ 富媒体搜索结果并移除相关文档；HowTo 富媒体搜索结果更早之前就已停止提供。不要为了获得 Google 富媒体搜索结果而添加 `FAQPage` 或 `HowTo`：

- FAQ 更新：https://developers.google.com/search/updates#faq-deprecation
- HowTo 更新：https://developers.google.com/search/updates#how-to-deprecation

当 FAQ 和步骤内容对用户有帮助时，可以继续保留。其他使用方可能仍能识别 Schema.org 类型，但这是另一项需要明确限定范围的主张。

## 垃圾内容政策

来源：https://developers.google.com/search/docs/essentials/spam-policies

一旦确认符合相关情形，应视为高风险。相关政策包括伪装真实内容、门页滥用、过期域名滥用、隐藏文字/链接滥用、关键字堆砌、链接垃圾内容、机器生成的流量、大规模内容滥用、抓取内容滥用、网站声誉滥用、欺骗性重定向、内容单薄的联属营销以及用户生成的垃圾内容。

使用 AI 辅助本身并不违规。主要为了操纵排名、且没有为用户增加价值的大规模内容生产，可能违反大规模内容滥用政策。应评估内容目的、原创性、人工监督和用户价值。

拒绝链接不是常规的链接清理手段。Google 仅在以下情况下建议使用：存在大量垃圾、人工操纵或低质量链接，且这些链接已经导致或很可能导致人工处置：https://support.google.com/webmasters/answer/2648487

## 实用、可靠、以用户为中心的内容

来源：https://developers.google.com/search/docs/fundamentals/creating-helpful-content

把 Google 的自评问题作为质量判断框架，而不是机械评分表。信任是 E-E-A-T 的核心；E-E-A-T 不是一个标签，也不是单一、可测量的排名因素。应检查原创价值、第一手经验、专业能力、来源是否清晰、主张是否准确，以及页面能否完成用户的预期任务。

## 生成式 AI 功能

主要来源：https://developers.google.com/search/docs/fundamentals/ai-optimization-guide

Google 表示，AI Overviews 和 AI Mode 仍然建立在搜索的核心系统之上。应优先保障常规技术资格，并打造独特、有价值、专家主导的非同质化内容。

Google 明确表示，Google Search 不会使用 `llms.txt`，搜索可见性也不要求极小内容切块、AI 专用改写、虚假提及或专用 AI schema。`Google-Extended` 不控制内容是否在 AI Overviews/AI Mode 中出现、被链接或用于 grounding，也不影响 Google Search 的收录或排名；Google 同时将它列为限制相关模型训练用途的控制项：https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers#google-extended

Search Console 来源：

- 生成式 AI 收录控制项：https://support.google.com/webmasters/answer/16908024
- 生成式 AI 效果报告：https://support.google.com/webmasters/answer/16984139

截至本次核验，该效果报告仍在逐步推出，支持页面、国家/地区、设备和日期维度，但不提供查询/点击字段。

## Search Console 与分析工具

来源：https://developers.google.com/search/docs/monitor-debug/google-analytics-search-console

Search Console 衡量访问发生前的活动；分析工具衡量用户在站内的行为。两者数值不会完全一致。只能在落地页、国家/地区、设备和日期等共有的聚合维度上结合数据。不要声称能够确定性地把查询归因到转化。

GA4 当前支持的归因模型记录于：https://support.google.com/analytics/answer/10596866 。历史上的首次点击、线性、根据位置和时间衰减模型已不再是 GA4 当前的报告选项；只有在明确标注为自定义离线模型时才能使用。

## 发现记录格式

```text
严重程度/优先级：
观察证据：
官方规则或建议：
URL 与核验日期：
受影响范围：
修复或实验：
产物验证：
结果指标与复核窗口：
```

仅当存在已验证的阻断问题、安全/垃圾内容/人工处置风险或重大业务故障时，才使用 `Critical`。缺少可选增强项不属于 `Critical`。
