# B2B 视频搜索与证据资产手册

最近核验：2026-07-11。

视频在能展示真实产品、工艺、测试、故障或专家判断时，是文本难以替代的一手资产。是否投入由目标 SERP、买家任务、生产能力和合格业务结果决定；不使用“YouTube 是 AI 最强信号”等第三方相关性数字作为普遍结论。

Google 官方入口：

- Video SEO：https://developers.google.com/search/docs/appearance/video
- Video structured data：https://developers.google.com/search/docs/appearance/structured-data/video
- Video sitemap：https://developers.google.com/search/docs/crawling-indexing/sitemaps/video-sitemaps

上传、账号、出镜和公开发布由人类授权执行；Agent 可准备研究、脚本、metadata、transcript、schema/页面实现和复盘分析。

## 1. 先验证视频是否适合

检查：

- 目标市场 SERP/YouTube 是否实际出现视频，用户是在看流程、比较、排障还是验证供应商。
- 企业是否拥有可拍的一手证据，而不是只能做图库宣传片。
- 视频对应哪个已验证词族、页面和转化任务。
- 拍摄、合规、客户授权、技术复核和持续维护能力。

没有搜索/业务证据时先做小样本实验，不制定固定月更数量。

## 2. 高价值 B2B 类型

- 工厂/产线：展示真实设备、流程、产能边界和质量控制。
- QC/测试：显示方法、仪器、标准、样本条件与结果解释。
- 产品演示：帮助买家理解安装、兼容、维护和失败模式。
- 规格/选型：把复杂条件、单位和否决规则讲清。
- 案例复盘：呈现约束、基线、动作、测量和不可迁移部分。
- 专家答疑：回答 RFQ、销售和售后反复出现的真实问题。

真实准确优先于过度包装；音频、字幕、画面可辨识度和安全合规必须达标。

## 3. YouTube 选题与页面连接

- 选题来自 `.vibio/trackers/keywords.md`、GSC、站内搜索、RFQ/CRM 和 paid search terms。
- 标题/描述使用目标市场真实措辞，准确说明视频内容，不堆关键词或伪造年份/结果。
- 描述链接使用合适 UTM，并指向完成下一步任务的页面。
- 按 YouTube 当前规则添加准确章节/时间戳；不能保证一定生成 Google Key Moments。
- 字幕和翻译必须人工复核产品名、牌号、单位、标准和安全说明。
- 播放列表按真实产品/任务组织；Shorts 仅在适合该受众和素材时作为实验，不设固定产量。

YouTube 的观看、留存和订阅是平台指标，不等同于 SEO 或收入。优先观察目标市场观看、合格站点访问、RFQ 和 CRM 阶段。

## 4. 站内视频页

Google 更容易在“视频是主内容、用户可直接观看”的 dedicated watch page 上理解视频。核心视频需要搜索展示时，创建有独特 URL、稳定缩略图、说明和相关文字内容的 watch page。

文章或产品页可嵌入辅助视频；只要多个 schema 都真实、无冲突，独立 VideoObject 与 Article/Product graph 可以共存。不能声称“两个顶级 schema 会互相冲突”。

VideoObject 属性按实时 Google 文档配置。通常包括准确的 `name`、`description`、`thumbnailUrl`、`uploadDate`，以及可用的 `contentUrl` 或 `embedUrl`。Clip/SeekToAction 只在当前资格和实现条件满足时使用。

Schema 必须对应页面可见、可播放的视频；缩略图 URL 稳定且可抓取。

## 5. Transcript 与辅助内容

提供经过校对的 transcript、章节摘要、关键数据、标准和相关链接，可以帮助无声/听障用户、页面理解和文本搜索。不要把 transcript 描述成保证 AI 引用的技巧。

Transcript 不应只是自动字幕原样堆叠；修正术语、说话人和明显错误，同时保持内容真实，不添加视频中未出现的虚构事实。

## 6. 托管与性能

选择 YouTube、其他平台或自托管时比较：

- 目标用户的发现渠道。
- 数据/品牌控制、隐私和地区可用性。
- 页面性能、cookie/consent、广告和推荐干扰。
- 视频索引、稳定 URL、字幕和维护成本。

第三方 iframe 可能显著增加资源和主线程开销。用 Lighthouse/RUM/CrUX 测量目标页；需要时采用 facade/点击加载，但确认可访问性、consent、播放和分析仍正确。不能强制所有页面使用同一实现或承诺固定毫秒提升。

## 7. 视频 sitemap 与索引

当重要视频难以通过普通 crawl 被发现、或站点视频规模较大时使用 video sitemap。只提交页面上真实可观看的视频和准确 metadata。GSC Video indexing/report 用于诊断，不承诺 48 小时收录。

## 8. 分发

LinkedIn、行业平台、邮件、销售资料和客户/伙伴频道按目标受众选择。原生上传还是外链，用各平台当前文档和自己的实验决定；不使用固定“-30% 至 -60% 触达”等无来源数字。

所有对外视频必须确认客户授权、商标、员工肖像、工厂安全、保密与出口/合规边界。

## 9. 测量

建立 video -> page -> CRM 的链路：

```text
video/topic | market | source | qualified views | site visits |
landing page | generated leads | qualified leads | opportunities | won |
coverage/caveat
```

同时查看：视频索引状态、目标查询/页面的 Search 表现、UTM 访问、表单自报来源和 CRM 结果。自报归因是辅助证据，不是唯一真相。

不承诺 90 天出询盘、6-12 个月复利、固定回访率或订阅时间。用项目自己的 cohort 设基线和停止条件。

## 10. 与模式集成

| 模式 | 接入点 |
|---|---|
| KEYWORD | 标记哪些已验证任务需要视觉演示；不另造未验证视频词库 |
| WRITE | 文章与视频共享一手素材，按任务决定 transcript/嵌入/watch page |
| FIX | 落地 VideoObject、watch page、性能、sitemap 并验证渲染结果 |
| LINK | 将真正有引用价值的视频用于媒体/伙伴 outreach；不称为最强 AI 信号 |
| REVIEW | 按目标市场、页面和 CRM cohort 判断是否继续投入 |

## 不要做

- 不把企业宣传片、Shorts、YouTube 托管或固定月更量当通用答案。
- 不跳过目标市场和买家任务验证。
- 不发布未经复核的技术字幕/自动配音。
- 不给不存在、不可播放或页面不可见的视频加 schema。
- 不把 transcript、VideoObject 或视频提及承诺成 AI 引用/排名提升。
- 不越权上传、发帖或代表企业公开发言。
