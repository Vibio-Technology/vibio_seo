# SERP 展示机会诊断

SERP 功能是特定查询、市场、设备和时间下的展示形态，不是可保证“拿下”的固定排名位。目标是判断某种展示是否能帮助目标买家完成任务，并用当前官方资格、站点证据和受控复盘决定投入，而不是套用通用 CTR 或格式公式。

## 一、先限定观察

每次记录：

```text
Query / query class:
Target country, language and device:
Observed on / access context:
Feature and owning/cited URL:
Our current page / task / eligibility:
Business relevance:
Evidence level and limitations:
```

SERP 会因位置、语言、设备、时间、账号状态和搜索系统实验变化。单次截图只能证明一次观察；第三方 SERP 数据也要标注采集日期、市场、设备、样本和字段定义。

## 二、先判断是否值得做

按以下顺序决策：

1. **需求与业务**：该查询/任务是否来自目标市场的 GSC、CRM/RFQ、站内搜索、客服或经核验的 paid search terms？
2. **页面任务**：已有页面是否应完成该任务，还是需要合并、重构或拒绝该机会？
3. **技术资格**：页面能否抓取、索引、渲染，canonical 和目标市场信号是否正确？
4. **功能资格**：该展示当前是否存在官方文档或可重复观察，页面是否满足真实内容和技术要求？
5. **信息增益**：能否提供原创数据、第一手经验、准确比较、清晰媒体或更好的决策支持？
6. **可测性**：能否定义实施、搜索与业务指标，以及停止/回滚条件？

不要因功能醒目或工具标注“机会”就提高优先级。优先级应综合业务价值、已有需求证据、资格差距、信息增益、资源、置信度和可逆性。

## 三、按展示类型诊断

| 展示/形态 | 当前机会判断 | 可执行动作 | 不能声称 |
|---|---|---|---|
| Featured snippet | 目标市场样本中确实出现，且页面已服务该任务 | 在自然位置给出准确、完整、可独立理解的解释、步骤或比较，并使用语义化 HTML | 固定字数、列表项或表格尺寸会获得 snippet；它有固定 CTR |
| People Also Ask | 问题与真实买家任务一致，并被一方证据支持 | 将有用答案放入最合适页面；具体方法见 `references/paa-gap-analysis.md` | PAA 展开次数等于搜索量或完整长尾需求 |
| 图片结果 | 视觉内容能帮助识别、比较、安装或验证产品/场景 | 使用原创清晰图片、相关上下文、准确 alt、稳定可抓取 URL、合适尺寸与性能；按需使用 image sitemap | 关键词堆砌文件名/alt 会提升排名，或图片结果有固定点击率 |
| 视频结果 | 演示、操作、验证或评测确实需要视频 | 提供可播放的高质量视频、相关页面文本、稳定缩略图和当前支持的 VideoObject 属性；需要时使用视频 sitemap | 任何嵌入视频都能获得视频展示，或 schema 是排名信号 |
| Product/商家等富媒体结果 | 页面对应真实、当前受支持的类型 | 对照最新 Search Gallery 与政策，实现可见内容一致的必需/建议字段并验证 | 获得资格等于一定展示、排名提升或 AI 引用 |
| Local results | 业务确实服务该地区并满足平台资格 | 维护准确 Business Profile、官网实体/服务信息、评价响应和本地转化测量 | 建若干换城市名的门页即可进入 local pack |
| Sitelinks/站点名称 | 品牌导航和站点结构存在真实问题 | 使用清晰、稳定、可抓取的架构和内部锚文本；按当前文档完善首页 WebSite/站点名称信号 | 可以手动选择 sitelinks 或保证显示数量 |
| Knowledge panel | 品牌/实体识别对业务重要 | 保持官网、组织信息和可核验外部资料一致，并按官方渠道认领可管理面板 | 增加某种 schema 会自动生成面板或提升自然排名 |
| AI Overviews / AI Mode | 该渠道对业务重要且能做带日期的重复观察 | 做好常规技术资格，提供独特、可靠、专家主导的内容和良好页面体验 | 需要专用 GEO 文本、微型切块、`llms.txt`、AI schema 或固定首段长度 |

Google 已停止 FAQ 和 HowTo 富媒体搜索结果。FAQ 或步骤内容只有在帮助用户完成任务时才保留；不要以 `FAQPage`、`HowTo` 或“扩展 PAA”为 Google 富媒体结果目标。

## 四、内容与技术实施

- 先回答用户问题，再选择段落、列表、表格、图片或视频。格式由信息本身和可访问性决定，不机械复制当前赢家。
- 标题与小标题要准确描述内容；不要求逐字匹配查询、固定词数或关键词密度。
- 原创数据和经验应提供方法、日期、市场、样本和限制；引用外部数据时链接规范来源。
- 结构化数据必须与可见内容一致，只实现当前受支持且真实适用的类型，并通过语法与资格验证。
- 图片、视频和交互内容不能替代关键文本信息；验证移动端、性能、资源抓取和许可。
- 不为多个近义查询制造相似页面或门页。一个页面覆盖同一主要任务，独立意图才建立独立 URL。
- AI 搜索仍建立在基础 SEO 与质量系统之上。不要为了机器引用牺牲目标市场语言、阅读体验或业务准确性。

## 五、实验与复盘

对高价值机会建立 change ID，保存观察 SERP 和页面前后快照。尽可能按相似页面、查询类别或市场分批测试；没有对照时使用稳定趋势并明确局限。

按层测量：

1. **实施**：内容、媒体、标记和内链在渲染结果中正确。
2. **资格**：抓取/索引正常，当前官方验证工具或 Search Console 未显示适用错误。
3. **搜索**：GSC 的相关查询组合、展示、点击、实际标题/展示形态和位置分布；功能归属用带日期的目标市场抽样核验。
4. **业务**：自然落地页 cohort 的参与、合格转化、销售管道或收入护栏。

功能出现不等于业务成功，功能消失也不必然代表页面退化。不要使用通用 CTR、固定排名区间或固定检查周期。观察窗口由项目抓取延迟、SERP 波动、样本量和预先定义的最小有意义效果决定；采用 `references/review-engine.md` 的 verdict。

## 六、可选能力与降级

| 需要 | 可选能力 | fallback |
|---|---|---|
| 目标市场 SERP/功能 | `seo-dataforseo` | 浏览器或用户提供截图做带日期、地区、设备的有限抽样；明确非穷尽 |
| GSC/索引 | `seo-google` | 请求导出；不可得时只验证公开 SERP 与实施产物 |
| 抓取/渲染 | `seo-firecrawl`、`seo-drift` | 对目标 URL 使用浏览器/curl，保存 HTML 和截图快照 |
| 结构化数据 | `seo-schema` | 解析 JSON-LD，对照最新官方 Search Gallery/政策和可用验证工具 |
| 图片/视频结果 | 专业 SERP/媒体工具 | 人工核验资源可抓取性、页面上下文与有限 SERP 样本 |
| 业务结果 | GA4/CRM | 请求自然落地页 cohort 导出；缺失时不评价收入影响 |

任何外部能力都不是前提。能力缺失时缩小结论，绝不能虚构功能存在、归属、CTR、排名、流量或引用。

## 七、官方核验入口

- 搜索展示功能库：https://developers.google.com/search/docs/appearance/structured-data/search-gallery
- Featured snippet 控制：https://developers.google.com/search/docs/appearance/featured-snippets
- Google 图片最佳实践：https://developers.google.com/search/docs/appearance/google-images
- 视频最佳实践：https://developers.google.com/search/docs/appearance/video
- Sitelinks：https://developers.google.com/search/docs/appearance/sitelinks
- 站点名称：https://developers.google.com/search/docs/appearance/site-names
- AI 功能优化基线：https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- FAQ 停止更新：https://developers.google.com/search/updates#faq-deprecation

行动前重新核验易变功能的实时官方页面，并记录 `verified_on` 和采用的准确论断。

## 八、机会记录

```markdown
| Query class | Market/device | Observed feature/date | First-party demand |
| Current URL/task | Eligibility gap | Information gain | Action |
| Evidence/confidence | Implementation QA | Search result | Business result |
| Verdict | Next check/stop condition |
```
