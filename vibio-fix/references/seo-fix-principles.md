# SEO 修复目标规范

最近核验 Google 官方资料：2026-07-11。

本文定义与技术栈无关的目标状态；各 stack adapter 负责说明具体落点。正确性以 HTTP 行为和渲染结果为准，不能只看源码。

把建议当作硬性要求前，先读 `google-search-docs.md` 与 `evidence-policy.md`。

## 1. 搜索资格与可索引性

对希望参与排名的页面确认：

- Googlebot 能访问 URL，并能渲染关键内容和资源。
- URL 返回真实的成功状态；迁移、删除、错误使用正确响应。
- 没有误加的 `noindex`、snippet 限制、登录墙或 robots 阻断。
- 重要内链是可抓取的 `<a href>`。
- 渲染结果里存在有价值、可索引的主内容。

满足这些条件只代表具备资格，不保证一定收录。

## 2. URL 与 canonical 意图

- 一份内容有一个稳定的首选 URL。
- 重定向、内链、sitemap、hreflang 和 canonical 信号一致。
- 跟踪、筛选、会话参数不会产生失控的可索引重复 URL。
- canonical 页面推荐使用 self-canonical；仅真正重复内容才跨页 canonical。

错误 canonical 比缺少 self-canonical 风险更高。有 GSC 时核对 Google 选择的 canonical。

## 3. Title 与 snippet

重要页面应有简洁、准确、互不重复的 title，且与可见内容和搜索意图一致。Meta description 用来概括页面、帮助用户判断是否点击；Google 可能自行生成其他 snippet。

Google 没有固定字符上限。检查桌面与移动端的实际呈现，不使用 `50-60` 或 `150-160` 字符作为硬闸门。

## 4. 主内容与标题结构

- 页面明确表达主要主题或任务，并兑现搜索结果中的承诺。
- 标题层级帮助读者和辅助技术理解内容，不能只为视觉样式使用。
- 原创证据、专家判断、产品事实、案例、图片或数据形成非同质化价值。
- 关键事实不能藏在失效交互或错误的客户端渲染之后。

一个清晰 H1 是推荐约定，不是 Google 的通用硬要求；不能因多个 H1 就自动判为 Critical。

## 5. 结构化数据

仅在 JSON-LD 真实对应可见内容、且服务于当前仍受支持的搜索功能时使用。对照最新功能文档和 Rich Results Test 验证 required/recommended 属性。

常见有效场景可能包括：首页的 Organization 与 WebSite/site-name，Product/Merchant listing、Breadcrumb、Article、Video、LocalBusiness、JobPosting、Event，以及 Google Search Gallery 当前仍列出的其他类型。

禁止：

- 强制全站输出 Organization + WebSite。
- 为排名或 AI 引用添加已停用、无支持的类型。
- 为 Google 富结果收益添加 `FAQPage` 或 `HowTo`；这两项功能已停止。
- 标注用户看不到的内容或企业无法证实的声明。

结构化数据提供机器可读线索，并可创造受支持搜索功能的资格；不保证功能展示、排名或生成式 AI 展示。

## 6. 内部发现与信息架构

- 重要页面可通过相关导航和上下文链接到达。
- 希望参与搜索的落地页不能成为孤儿页。
- 锚文本自然说明目标内容，避免重复精确匹配操纵。
- 新页面发布时获得相关旧页面的入链。
- 商业路径清楚，但不强套通用点击深度或每千字链接配额。

完整操作流程见 `link-architecture.md`。

## 7. 图片与视频

- 有意义的图片使用有帮助的 alt；装饰图片按无障碍规范使用空 alt。
- 尺寸、比例和响应式资源避免 CLS 与不必要传输。
- 首屏以下媒体可延迟加载，但不能隐藏主内容或延迟 LCP 资源。
- 用户需要检查真实产品、流程或结果时，优先原创媒体。
- 视频页面只在符合当前 VideoObject 与 watch-page 指南时做对应优化。

## 8. Sitemap 与 robots

- Sitemap 只列希望被发现的 canonical、可索引 URL，并遵守协议限制。
- Robots 不能阻断重要内容/资源，也不能把 robots.txt 当作 `noindex` 使用。
- 在 robots.txt 声明 sitemap 有助于发现，但不能替代内部链接。

普通页面不得使用 Google Indexing API；它只支持合规的 JobPosting 和直播 BroadcastEvent 页面。

## 9. 国际化站点

- 每个本地化页面有属于该语言/地区的可索引 canonical。
- Hreflang 使用有效语言/地区代码，并保持 alternate 的双向对应。
- 用户无需只依赖 IP 跳转，也能使用语言/地区导航。
- 只有确实存在默认语言选择器或全球页时才使用 `x-default`；它不是每组都必需。

## 10. 页面体验与转化

- 主内容和核心转化在目标设备上可正常完成。
- 有条件时用 CrUX 或其他 RUM 判断真实用户表现；lab 测试用于诊断，不能证明线上效果。
- 按用户与业务影响修复侵入式弹层、布局偏移、表单失效、控件不可访问和关键交互延迟。
- B2B 测量区分新线索、合格线索、销售跟进/接受、成交与淘汰。

页面体验与 Core Web Vitals 可能影响搜索和业务，但任何单项得分都不保证排名变化。

## 11. 社交元数据

Open Graph/Twitter 元数据应准确代表页面，图片需可访问、URL 为绝对地址，尺寸与声明一致。社交预览改善分发和点击质量，不能称为直接 Google 排名修复。

## 12. Google AI 功能与其他答案引擎

按 `geo-dominance.md` 和 `geo-audit.md` 执行：

- 基础仍是正常 Search 资格与原创、专家主导的非同质化内容。
- Google 忽略 `llms.txt`，它不是必修项或评分项。
- `Google-Extended` 不控制内容是否在 AI Overviews/AI Mode 中出现、被链接或用于 grounding，也不影响 Google Search 收录/排名；它另用于限制相关模型训练用途。
- 细碎分块、AI 专用改写、虚假 mentions 和特殊 AI schema 都不是 Google 要求。
- 平台专项工作必须有该平台官方文档或可测实验支持。

## 验证协议

1. 按技术栈运行 build、lint、类型检查。
2. 对代表性页面检查响应状态、headers 与渲染 HTML。
3. 真正解析 JSON-LD，并验证当前受支持功能，不能只 grep 字符串。
4. 从服务产物检查 robots、sitemap、canonical、hreflang、内链和媒体 URL。
5. 分开报告“产物已验证”与“抓取/收录/排名效果待观察”。
6. 在 `.vibio/changelog.md` 记录目标指标和复盘窗口。

GSC URL Inspection 或 request indexing 可用于诊断或优先处理少量关键 URL，但不保证收录，也不能替代可发现性、sitemap 与内容质量。

## 修复优先级

综合影响、证据、范围、成本和依赖：

1. 已确认的访问、索引、canonical、状态码或 manual action 阻断。
2. 阻止正确决策的测量故障。
3. 关键页的意图错误、规模化重复或非同质化价值缺失。
4. 内部发现与信息架构缺口。
5. 当前受支持的搜索展示资格与 snippet 改善。
6. 页面体验和转化摩擦。
7. 可选分发、社交或平台实验。

任何 checklist 项都不能越过项目的主瓶颈。
