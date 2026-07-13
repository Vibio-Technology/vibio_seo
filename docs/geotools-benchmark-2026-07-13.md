# Geotools.online 产品与实现基准测试

测试日期：2026-07-13

目标站点：`https://geotools.online/`

用途：为 Vibio SEO 的 SaaS 首页、统一项目入口、自动流程与报告体验提供可迁移证据，不用于复刻对方评分模型或文案。

## 1. 结论先行

- **观察事实**：Geotools 的主流程足够直接：一个 URL 入口、少量范围选项、独立进度页、分层结果和 JSON/HTML 导出。桌面与移动端的主要任务均可完成。
- **观察事实**：网站存在上线级缺陷，包括 HTTP 不跳 HTTPS、无 HSTS、`www` TLS 失败、任意不存在路径返回首页 `200`、博客工具 canonical 错指首页，以及若干对比度和状态播报问题。
- **观察事实**：评分由固定权重和启发式分析器产生。对 `example.com` 的本次单页运行给出 `29.8 / F`；其中 `llms.txt` 缺失被计为 0 分并进入高影响建议，性能 100 分则来自工具侧 9ms 请求。这些数字不能直接代表真实搜索表现、Core Web Vitals 或 AI 引用概率。
- **推断**：值得迁移的是任务编排和信息架构，不是评分外观。Vibio 应强化“一个项目档案 + 每项任务只补必要差异 + 可恢复自动流程 + 证据化报告”。
- **不采纳**：无证据综合分、`llms.txt` 必需论、模型渠道伪精确分，以及把源码观察写成“已收录/会引用”的表达。

## 2. 测试范围与环境

### 2.1 环境

| 项目 | 配置 |
| --- | --- |
| 浏览器 | Playwright Chromium |
| 桌面视口 | `1440 x 1000` |
| 移动视口 | `390 x 844`，启用 `isMobile` 与触控 |
| 网络目标 | Geotools 线上生产站 |
| 表单样例 | `https://example.com` |
| API 样例 | 单页、最多 1 页、关闭 AI 引用模拟、开启性能分析 |

### 2.2 覆盖内容

- 首页、博客检测/优化器、模型数据渠道、AI SEO 清单和 GEO 指南。
- 桌面/移动布局、导航、键盘、表单验证、加载、成功、断网与服务端错误。
- 分析提交、轮询、结果 JSON、HTML 报告和下载入口。
- 首页与博客页 metadata、robots、sitemap、结构化数据、HTTP/HTTPS、404 与常见图标资源。
- 基础可访问性：标题、landmark、标签、焦点、对比度、状态播报和横向溢出。

### 2.3 边界

- 未登录任何账户，未测试付费、后台管理或跨设备历史。
- 未向第三方 LLM 提交真实 API Key，因此博客优化器只验证表单与可见行为，不评价生成质量。
- 未进行并发、压力或破坏性测试。
- 只提交了一次正常的 `example.com` 单页分析；后续 GET 轮询和报告下载属于同一任务。
- 页面上出现的分数只用于理解该产品的呈现和数据合同，不作为 Vibio 的评估真值。

## 3. 页面矩阵

`PASS` 表示在本轮指定任务和视口内可用；不代表该页的 SEO、可访问性或内容结论全部合格。

| 页面 | 路由/HTTP | 桌面 | 移动 | 键盘/交互 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 首页与网站检测 | `/` | PASS | PASS | PASS | 主入口、范围选项、提交和结果链路可用 |
| 博客 GEO 检测与优化器 | `/blog-geo-checker` | PASS | PASS | PASS | 功能布局可用；metadata 与对比度另记 FAIL |
| 模型数据渠道 | `/model-data-channels.html` | PASS | PASS | PASS | 可达、无横向溢出 |
| AI SEO 清单 | `/ai-seo-checklist.html` | PASS | PASS | PASS | 可达、无横向溢出 |
| GEO 指南 | `/geo-guide.html` | PASS | PASS | PASS | 可达、无横向溢出 |
| 不存在页面 | 随机路径 | **FAIL** | **FAIL** | N/A | 返回首页 HTML `200`，属于 soft 404 |
| 缺失静态资源 | favicon/manifest/随机 PNG | **FAIL** | **FAIL** | N/A | 同样返回首页 HTML `200` |

补充观察：

- 五个导航目标均返回可见页面，初始加载未见功能性 console/page error。
- 两种视口均未发现页面级横向溢出或主要内容裁切。
- 移动端导航常显并换为两行，没有折叠菜单。因此“菜单开关/Escape 关闭菜单”应记为 `N/A`，不是菜单失效。
- 静态页跳转时观察到 Cloudflare RUM 请求中止；未影响目标页渲染，不据此判定业务请求失败。

## 4. 网站检测 API 与状态机

### 4.1 提交合同

端点：

```text
POST https://geotools.online/api/v1/analyze
Content-Type: application/json
```

单页请求：

```json
{
  "url": "https://example.com",
  "mode": "single_page",
  "max_pages": 1,
  "options": {
    "enable_ai_citation": false,
    "enable_performance": true,
    "competitors": []
  }
}
```

全站加 AI 模拟的界面合同：

```json
{
  "url": "https://example.com",
  "mode": "full_site",
  "max_pages": 50,
  "options": {
    "enable_ai_citation": true,
    "enable_performance": true,
    "competitors": []
  }
}
```

本次提交返回：

```json
{
  "id": "<job-id>",
  "status": "pending",
  "message": "分析任务已创建"
}
```

### 4.2 轮询与终态

轮询端点：

```text
GET /api/v1/analysis/{job-id}
```

前端约每秒轮询一次。代码将 `completed` 和 `failed` 视为终态，其余状态继续轮询。

```text
提交
  -> pending / 正在连接
  -> crawling / 非终态进度（progress + current_step）
  -> completed
       -> 页面结果
       -> /reports/{id}/json
       -> /reports/{id}/html
  -> failed
       -> error_message
```

- **观察事实**：初始 UI 先显示 spinner 与“正在连接”。
- **观察事实**：处理中展示百分比、进度条、当前步骤，以及“抓取页面、获取辅助文件、运行分析器、计算评分”四个阶段。
- **观察事实**：本次 API 附件实际观察到 `pending`、`crawling` 和 `completed`；`crawling` 时为 10% 并进入抓取阶段。前端会继续轮询任何非 `completed`/`failed` 状态，因此不据此猜测尚未观察到的其他枚举名。
- **观察事实**：成功响应包含 `progress: 100` 与 `current_step: "分析完成"`。
- **推断**：这种 202 + polling 适合无需长期保存用户密钥的确定性抓取任务；对 BYOK 模型任务，若要求关页后继续，则必须额外解决密钥和输入的服务端保留、加密、过期和重复计费治理。

### 4.3 错误与恢复

| 场景 | 观察结果 | 判定 |
| --- | --- | --- |
| 空 URL | 按钮禁用，Enter 不发请求 | PASS |
| `abc` / `example.com` | 原生 URL type mismatch | PASS，但浏览器提示为英文 |
| 有效绝对 HTTPS URL | 提交按钮启用 | PASS |
| 网络断开 | 输入保留、按钮恢复，`role=alert` 显示 `错误 / Failed to fetch` | 可恢复，文案 FAIL |
| 提交返回 503 | 显示 `Failed to submit analysis: 503` | 可恢复，未使用服务端 detail，FAIL |

Vibio 不应直接复制底层英文错误。至少应区分网络断开、限流、输入验证、抓取失败、模型失败与超时，并给出下一动作。

## 5. 结果 JSON 与 HTML 结构

### 5.1 JSON

完成响应顶层字段：

```text
id, url, mode, status, progress, current_step,
overall_score, grade, dimension_scores,
error_message, created_at, completed_at,
pages, recommendations
```

主要嵌套结构：

```text
dimension_scores.{dimension}
  name, label, score, weight, grade, findings_count, analyzers[]

pages[]
  url, status_code, title, overall_score, dimension_scores,
  findings.{analyzer}[], word_count

findings.{analyzer}[]
  analyzer, dimension, severity, title, description, details?

recommendations[]
  dimension, analyzer, severity, title, description,
  action, impact_score, page_url
```

观察到的设计优点：总览、维度、页面、发现和建议可以分别消费，适合前端渐进披露与机器导出。

需要避免的合同问题：

- `score`、`grade`、`impact_score` 只有数值，没有证据 ID、计算版本或置信区间。
- 同一个启发式发现会同时进入页面 findings 和 recommendations，消费端需要稳定 ID 才能去重和追踪修复。
- `performance` 的工具侧请求耗时与真实用户 Core Web Vitals 语义不同，不应共用“性能分”而不说明证据来源。

### 5.2 HTML

HTML 导出端点：

```text
GET /api/v1/reports/{job-id}/html
```

本次导出包含：

- 文档标题与 H1：`GEO 分析报告`。
- URL、生成信息和总分圆环。
- `维度评分`区块。
- `优化建议 (19)`区块。
- 自包含样式的静态报告容器。

交互结果页比 HTML 导出更丰富：总分圆环、五维雷达图、维度卡、可展开检查项、建议列表，以及 JSON/HTML 下载入口。优点是信息上限高；代价是结果页很长，默认展开策略需要控制。

## 6. `example.com` 实测摘要

本次单页、无 AI 模拟运行：

| 指标 | API 原值 | UI 近似显示 |
| --- | ---: | ---: |
| 综合 | 29.8 / F | 30 / F |
| 技术基础 | 53.5 / D | 54 / D |
| 结构化数据 | 20 / F | 20 / F |
| 内容结构 | 34.6 / F | 35 / F |
| E-E-A-T 信号 | 3 / F | 3 / F |

另一次开启 AI 引用模拟的界面结果曾显示 `40 / F`。该值来自另一配置，不与本次 `29.8` 做前后对比。

对分数的解释边界：

- **观察事实**：技术维度中 `llms_txt` 为 0 分、权重 0.1；“创建 llms.txt”被列为 `impact_score: 8` 的建议。
- **观察事实**：性能分析器给出 100 分，证据是工具侧“页面加载时间 9ms”和约 1KB HTML。
- **观察事实**：工具对一个极短示例页同时应用博客文章、FAQ、作者、评论、Cookie、实体深度等检查。
- **推断**：低分主要反映固定检查表与页面类型不匹配，不等同于该域名真实搜索质量低下。
- **不采纳**：Vibio 不把这些数值、字母等级或固定权重作为自己的评分依据。

## 7. 博客检测与优化器

`/blog-geo-checker` 包含两条路径：

1. 输入博客 URL，进入与主检测相近的文章检查流程。
2. BYOK 内容优化器，配置 LLM 平台、Base URL、API Key 和模型，再粘贴正文并补充目标关键词、语气和可选正文要求。

观察行为：

- 模型连接设置与文章任务输入分区，降低了每次任务的重复输入。
- 正文不足 100 字或没有必要输入时，“一键优化博客”不可用。
- 页面明确提醒 Key 不应保存到本站服务器，并提供三步使用教程。
- 优化结果区支持复制，教程预期输出包括 Markdown 文章、FAQ 和 Schema 建议。
- 本轮没有调用第三方 LLM，因此不声称 Key 是否实际落库，也不评价结果事实性。

可访问性问题：

| 元素 | 实测对比度 | WCAG AA 小字 |
| --- | ---: | --- |
| `.key-notice strong` | 3.42:1 | FAIL |
| `.security-reminder` | 3.27:1 | FAIL |
| 教程 mock input | 2.56:1 | FAIL |
| 教程 mock button | 4.10:1 | FAIL |

## 8. SEO、路由与可访问性缺陷

### 8.1 高优先级上线缺陷

| 缺陷 | 观察证据 | 风险 |
| --- | --- | --- |
| HTTP 不跳 HTTPS | `http://geotools.online/` 返回 `200` | 重复协议、弱安全入口 |
| 无 HSTS | HTTPS 响应未见 HSTS | 首次访问降级风险 |
| `www` 不可用 | 多次 TLS 建连失败 | 品牌入口和外链失败 |
| catch-all 返回 200 | 随机不存在路径返回首页 HTML | soft 404、抓取浪费、错误监控失真 |
| 缺失资源返回 200 | favicon、apple-touch-icon、manifest、随机 PNG 均返回首页 | 浏览器误解析、缓存与监控失真 |
| 博客 canonical 错误 | `/blog-geo-checker` canonical 指向首页 | 与 sitemap 收录该路由的信号冲突 |

### 8.2 Metadata 与结构化数据

首页通过项：

- `title`、description、canonical、robots、Open Graph 标题/描述、Twitter 标题/描述存在。
- `lang=zh-CN`、唯一 H1、viewport 正常。
- WebApplication、ItemList、FAQPage JSON 可解析。

缺陷：

- `/blog-geo-checker` 的 title、description、canonical、OG URL 继承首页；canonical 错指 `/`。
- `twitter:card=summary_large_image`，但没有 `og:image` 或 `twitter:image`。
- 没有有效 favicon 链接；相关资源请求还被 catch-all 伪装成 200。
- FAQPage 的三个问题没有出现在可见页面中。结构化数据不能替代用户可见内容。
- WebApplication 的 `sameAs` 指向站内指南、清单和 `llms.txt`，不符合“同一实体的外部权威标识”语义。
- `/robots.txt`、`/sitemap.xml`、`/llms.txt` 均为 200，但“文件存在”不证明搜索引擎或 AI 系统已抓取、采用或引用。

### 8.3 可访问性

通过项：

- 唯一 H1、主内容 landmark、表单名称、fieldset/legend、radio/checkbox 标签可读。
- Tab 导航、radio 的 ArrowRight 和 checkbox 的 Space 操作正常。
- URL 输入聚焦后有蓝色边框和约 4px focus ring；先前“移动焦点不可见”的判断不成立。
- 桌面和移动端没有页面级横向溢出。

需改进：

- 首页工具卡操作文字 `#1677ff` 对白色约 4.10:1，14px bold 仍低于 AA 4.5:1。
- 没有 skip link。
- Loading 未提供 `aria-busy` 或 `role=status`；仅有视觉 spinner 和文字。
- 网络错误虽有 `role=alert`，但直接暴露英文底层错误，缺少可操作建议。
- 原生 URL 校验提示在测试浏览器中为英文 `Please enter a URL.`，与中文页面不一致。

## 9. 可迁移模式

以下模式可迁移到 Vibio，但应使用 Vibio 自有术语、schema 和证据政策：

1. **一个主入口**：先收集项目级站点、市场、语言、合格转化和主要目标，各专项页只补当前决策必须知道的差异。
2. **单项与自动流程并存**：熟练用户可直接运行专项，新用户可从一个问题触发按依赖排序的自动流程。
3. **阶段进度**：展示“校验、收集证据、分析、生成报告”等真实阶段，不伪造百分比。
4. **渐进披露**：结果按“总览 -> 维度 -> 检查项 -> 建议 -> 原始证据”展开。
5. **建议绑定证据**：每条建议应指回观察项、影响边界、验证方式和下一动作。
6. **BYOK 分层**：提供商、Base URL、模型和 Key 属于连接设置；任务正文与业务约束属于运行输入。
7. **失败可恢复**：保留输入，说明失败阶段，在相同输入签名下允许继续。
8. **可审阅导出**：提供 JSON 和独立 HTML/Markdown，但字段必须稳定、可版本化并保留证据边界。

## 10. 明确不迁移

### 10.1 无证据评分

不迁移综合分、字母等级、雷达图精确数值或固定影响分，除非每个数值都能追溯到：

- 输入证据和采集时间；
- 计算版本、规则和权重；
- 页面类型与业务目标；
- 置信度和适用边界；
- 可重复的验证方法。

Vibio 的默认总览应显示“已观察/未观察/待验证、证据覆盖和严重度”，而不是伪精确健康分。

### 10.2 `llms.txt` 必需论

- `llms.txt` 可以是实验性辅助文件，但当前没有证据支持把缺失写成搜索或 AI 可见性的硬失败。
- 文件存在不等于模型会读取，更不等于引用或排名提升。
- Vibio 只能在用户明确要做该实验时给出低风险草案和验证计划，不能默认赋高权重。

### 10.3 模型渠道伪精确分

- 不给 ChatGPT、Claude、Perplexity 或其他渠道生成缺少真实查询、地区、时间、账号和引用记录的百分制分数。
- 不把源码中的品牌/Schema/FAQ 观察写成“某模型已引用”或“引用概率提升 X%”。
- 渠道结论必须来自可审计的实际响应、第一方日志或明确标注的人工抽样。

## 11. Vibio 落地决策

| 决策 | 采用方式 |
| --- | --- |
| 统一入口 | 保留一份项目档案；模式表单只显示该能力需要的最少字段，非必要字段折叠 |
| 自动流程 | 按证据条件决定恢复/复盘等步骤；输入签名变化后旧检查点失效 |
| 长模型请求 | 使用 POST 流式 heartbeat 保持连接并支持断连取消，不伪造百分比 |
| Durable 任务 | 严格 Key 不落库时不承诺关页续跑；如未来需要，先定义加密、TTL、删除和重复计费治理 |
| 审计总览 | 展示范围、严重度、分组发现、页面核验表和限制，不展示健康分 |
| 报告导出 | 使用版本化 Vibio schema，支持 Markdown、JSON 与自包含 HTML |
| 错误体验 | 统一中文化，区分网络、限流、验证、抓取、模型与超时，并给出恢复动作 |
| 上线门禁 | HTTPS 跳转、HSTS、`www` 策略、真实 404、canonical、sitemap/noindex 一致性必须通过 |
| 证据合同 | 每条发现必须包含来源、观察、影响边界、置信度和复验方式 |

## 12. 当前 Vibio 实现映射

本轮允许将 benchmark 的有效结构混入 Vibio，但以下实现只吸收信息架构和可靠性模式，不吸收 Geotools 的评分规则：

| Benchmark 结论 | Vibio 当前实现 |
| --- | --- |
| 总览先于长报告 | `src/components/AuditOverview.tsx` 先展示范围、严重度计数、证据分组、页面核验表和证据边界 |
| 只消费可识别 schema | `src/audit-overview.ts` 仅解析 `bounded_seo_artifact_inspection`，字段异常时不编造指标 |
| 结果渐进披露 | `src/components/ReportView.tsx` 将审计概览、模型报告、流程轨迹和证据清单分为可键盘操作的 tabs |
| 可审阅静态交付 | `src/report-export.ts` 生成自包含 HTML，并与 Markdown/JSON 下载并列；metadata 做 HTML 转义 |
| 长请求显示真实存活 | `src/app/api/analyze/stream/route.ts` 发送 accepted/heartbeat/complete/error NDJSON，不伪造百分比 |
| 断连停止上游消耗 | `src/lib/server/providers.ts` 接收 AbortSignal；客户端取消后中止 provider 请求 |
| 同一输入下自动流程 | `src/components/Workspace.tsx` 复用项目档案和模式草稿，失败时保留输入并按签名判断是否可继续 |

仍需后续评估但本轮不扩展的事项：

- 为 finding 增加稳定 ID、规则版本和证据引用，便于跨运行去重与修复追踪。
- 若未来要求关页后继续 BYOK 模型任务，必须先完成服务端密钥保留与删除政策设计；当前 heartbeat 不承诺 durable job。
- 上线环境仍需用真实域名验证 HTTPS 跳转、`www`、HSTS、404、canonical 和 sitemap，不能只依赖本地构建。

## 13. 证据附件

本轮截图保存在临时目录，未复制进仓库：

- `/tmp/geotools-desktop-home.png`
- `/tmp/geotools-mobile-home.png`
- `/tmp/geotools-processing-initial.png`
- `/tmp/geotools-stage-01.png`
- `/tmp/geotools-stage-02.png`
- `/tmp/geotools-stage-03.png`
- `/tmp/geotools-result-expanded.png`
- `/tmp/geotools-mobile-blog.png`
- `/tmp/geotools-desktop-network-failure.png`
- `/tmp/geotools-mobile-contrast.png`

本轮一次性 API 样例的任务 ID 仅用于复核上述合同，不应作为稳定测试 fixture。线上响应会随目标页面、分析器版本和运行时间变化。
