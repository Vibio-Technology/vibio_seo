# Bing Webmaster、IndexNow 与 AI Performance 官方基线

最后核验：2026-07-11。Bing Webmaster Tools、IndexNow 参与方和 AI 报告仍会变化；实施前重新读取实时文档。Bing 的产品行为不能直接外推到 Google 或其他平台。

## 官方来源

- Bing Webmaster Tools：https://www.bing.com/webmasters/about
- Bing Webmaster Guidelines：https://www.bing.com/webmasters/help/webmaster-guidelines-30fba23a
- Sitemaps：https://www.bing.com/webmasters/help/sitemaps-3b5cf6ed
- IndexNow 协议：https://www.indexnow.org/documentation
- IndexNow FAQ：https://www.indexnow.org/faq
- IndexNow 参与搜索引擎：https://www.indexnow.org/searchengines
- Bing AI Performance public preview 公告：https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview

## Bing 技术诊断顺序

1. 验证正确站点/协议/主机的所有权，并记录报告时区和日期范围。
2. 提交只包含首选、可索引 URL 的 sitemap；它用于发现，不保证抓取、索引或排名，也不替代可抓取内链。
3. 使用 URL Inspection、索引/抓取报告和服务器日志核对 Bingbot 实际状态，不以 `site:` 查询数量作索引清单。
4. 修复真实状态码、robots、canonical、渲染、重复 URL 和内容质量问题后，再使用 IndexNow 通知变化。
5. 将 Bing 搜索表现、AI 引用、站内分析和业务转化分开保存；只在共享聚合粒度上做描述性比较。

## IndexNow：通知不等于收录

IndexNow 用于通知参与搜索引擎某个 URL 已新增、更新或删除。提交时验证 API key 与 host 归属，只提交该 host 上实际发生变化的规范 URL，并监控返回码和重试；不要无期限重复提交未变化 URL。

协议对返回码的定义包括：

- `200 OK`：URL 或 URL 集已成功提交；官方文档同时明确，**200 只表示搜索引擎已收到 URL**。
- `202 Accepted`：请求已收到，但 key 验证仍待处理。
- `400/403/422/429`：分别检查格式、key、host/URL 归属和请求频率等问题，不把失败请求记为已通知。

收到通知后，搜索引擎仍会依据自己的抓取配额、调度、质量和索引判断决定是否抓取与收录。IndexNow FAQ 明确表示提交不保证立即索引；不同参与引擎也可做出不同决定。因此：

- `200` 不能写成“已抓取”“已收录”或“已排名”；
- IndexNow 不能替代 sitemap、内部链接、正确状态码、可抓取内容和质量；
- 成功标准分层为 `received`、`bot-fetched`、`indexed`、`search-visible`，每层使用对应证据；
- 用站长工具 URL 检查、索引报告、服务器日志和搜索表现确认后续状态。

## Bing AI Performance 的证据边界

截至核验日，该功能仍标为 **public preview**。官方公告说明覆盖 Microsoft Copilot、Bing 中的 AI-generated summaries 和部分合作方集成；这不是所有 AI 平台或所有回答的完整观测面。

| 字段 | 官方含义 | 不能推出 |
|---|---|---|
| Total Citations | 选定期间作为来源显示的引用总数 | 回答中的位置、点击、排名或转化 |
| Average Cited Pages | 每日作为来源显示的本站唯一页面平均数 | 页面权威、排名或在单个回答中的作用 |
| Grounding queries | AI 检索已引用内容时使用的关键短语；官方称其为总体引用活动的样本 | 完整用户查询集、搜索量或用户原话 |
| Page-level citation activity | 特定 URL 在支持的 AI 回答中被引用的次数 | 页面重要性、排名或展示位置 |
| Timeline | 支持范围内引用活动随时间变化 | 因果增量、流量或收入 |

把 AI Performance 当作平台内的描述性可见性信号：记录报告版本、支持范围、日期和筛选；使用 cited pages 与 sampled grounding queries 发现内容核验机会；再用分析平台和业务数据检查可观测访问与结果。引用增加不能自动称为 SEO/GEO 成功，下降也不能自动归因于单次页面改动。

Bing 表示其支持的 AI 体验会尊重 `robots.txt` 等内容所有者控制。控制可访问性会改变可用内容范围，但不构成获得引用的优化手段或保证。

## 复核记录

```text
Property/host:
Bing report and date range:
Sitemap status:
IndexNow URL/change type:
IndexNow response: received | pending-key | failed
Bingbot fetch evidence:
Index evidence:
Search performance evidence:
AI Performance surface/version:
Citation metric and coverage caveat:
Analytics/business evidence:
Conclusion: observed | directional | experiment-supported | inconclusive
```
