# PAA 与问题级需求缺口分析

People Also Ask（PAA）和生成式搜索回答可以帮助发现目标市场正在使用的措辞与子任务，但它们是动态 SERP 样本，不是完整查询数据库、搜索量或排名保证。问题是否进入内容计划，必须由一方需求、页面任务、信息增益和业务价值共同决定。

## 一、定义研究问题

开始前记录：

```text
Seed topic / product:
Target country, language and device:
Buyer stage and primary business outcome:
Existing page / intended page task:
Available first-party sources:
SERP collection method and date:
Decision this research must inform:
```

种子词应优先来自 GSC、站内搜索、CRM/RFQ、销售/客服记录、产品专家和经人工核验的 paid search terms。广告数据用于验证买家语言、意图和落地页学习，不能证明自然排名或成为独立广告运营任务。

## 二、采集 PAA 样本

1. 在目标国家、语言和设备环境中查询经验证的种子词，保存日期和可复查证据。
2. 记录当前可见的 PAA 问题、来源 URL、答案形态和所属页面任务。
3. 必要时展开相关问题以发现新的措辞；当新增问题不再改变词族、页面映射或决策时停止。
4. 对关键问题在不同种子词、时间或设备做有限复采，标记稳定出现与一次性观察。
5. 保存原文和规范化版本。合并真正同义的问法，但保留语言、市场、产品型号、比较对象或买家阶段造成的意图差异。

PAA 的问题数量和展开次数由界面动态生成，受地区、设备、时间和交互影响。不得把出现频率、展开层级或问题总数换算成真实搜索量、竞争度或“零竞争机会”。只有供应商能说明采样与指标定义时，第三方频率才可作为有限 E4 观察。

## 三、交叉验证需求

为每个问题建立证据列：

| 来源 | 能说明什么 | 不能说明什么 |
|---|---|---|
| GSC 查询/页面 | 该站已获得的搜索曝光与点击，受匿名化和聚合限制 | 全市场搜索量或查询到转化 |
| CRM、RFQ、销售/客服 | 真实买家疑问、阶段、市场和商业摩擦 | 搜索需求规模 |
| 站内搜索/支持工单 | 现有访客找不到或难以完成的任务 | Google 排名机会 |
| Paid search terms | 实际触发广告的用语、意图和落地页学习 | 自然排名、自然 KD 或 SEO 增量 |
| Keyword Planner/第三方工具 | 在其定义、市场和日期范围内的需求估算 | 精确流量或页面成功率 |
| PAA/自动补全 | 当前 SERP 的措辞和问题关系 | 完整长尾集合、真实查询量或买家身份 |
| 竞品页面 | 当前公开覆盖、证据与表达差异 | 某内容为何排名或真实业务效果 |

至少说明哪些问题只有 SERP 观察，哪些得到一方证据支持。数据冲突时保留来源与差异，不用一个无来源分数抹平。

## 四、AI 回答与引用观察

当目标市场确实出现 AI Overviews 或其他生成式回答时：

1. 保存查询、市场、设备、日期、回答、引用链接和访问状态。
2. 核验引用页面实际是否支持回答中的相关主张，不只记录域名。
3. 标出未提供来源、来源不充分、信息过时或缺少目标市场细节的主张。
4. 评估本企业能否提供更可靠的一手数据、方法、专家解释或决策工具。
5. 通过重复抽样确认观察是否稳定；无法复现时只保留方向性证据。

“回答中没有引用”不证明市场没有优质内容，也不代表发布页面后被引用概率高。生成式回答主动提及某主题也不证明搜索量或商业需求。对 Google，AI Overviews/AI Mode 仍依赖基础 SEO 与核心质量系统，不需要专用 GEO 文本、`llms.txt`、AI schema 或固定段落长度。

如果 Search Console 当前提供生成式 AI 报告，严格按其正式维度使用。截至 `references/google-search-docs.md` 的核验口径，该报告不能用于问题级点击或确定性引用归因；普通 Web 数据也不能反推出 AI 功能表现。

## 五、缺口矩阵与页面映射

```text
Question / normalized task:
Market / buyer stage:
Evidence sources and dates:
Existing URL and coverage quality:
Competitor/source coverage:
Accuracy or decision risk:
First-party information gain available:
Business relevance:
Recommended page: existing / new / merge / reject / research
Confidence and missing evidence:
```

缺口分为：

- **自己的缺口**：任务属于现有页面，但页面没有准确完成；
- **市场证据缺口**：多个公开来源都缺少可验证信息，而企业有一手能力补足；
- **表达缺口**：信息存在但目标市场措辞、格式或可发现性差；
- **非缺口**：问题与目标买家无关、已有页面已充分满足，或无法可靠回答；
- **待验证**：仅有一次 PAA/AI 观察，尚不足以投入生产。

不要用固定加分或“集体留白即最高优先级”。使用 `now / next / later / reject`：综合一方需求、商业价值、信息增益、准确性风险、已有页面匹配、产能和证据置信度，并写明 why。

### URL 决策

- 同一主要任务的问题应融入最合适的已有页面，放在用户需要答案的位置，不自动堆到页尾 FAQ。
- 只有当问题代表独立、持续、值得搜索进入的任务，且现有页面无法自然承接时才建立新 URL。
- 多个页面争夺同一任务时优先合并或重映射，避免近义问句页面和门页。
- 无法提供可靠答案、可能造成法律/安全误导或不服务业务范围的问题应拒绝或交专家审核。

## 六、内容规格

- 开头清楚回答当前小节的问题，但长度和位置由复杂度、风险与阅读体验决定，不使用固定字数。
- 选择段落、步骤、表格、图像、视频或工具来准确表达信息，而不是机械复制 PAA 当前格式。
- 对规格、价格、标准、法规和测试结论注明目标市场、单位、版本、日期、方法、来源与限制。
- 优先一手数据、真实案例、产品专家和可验证过程；不得从竞品内容改写出未经核验的答案。
- title、H1/H2 和内部锚文本描述页面任务，不要求逐字匹配 PAA 问句或关键词密度。
- FAQ 内容只有在帮助用户决策时才采用。Google 已停止 FAQ 和 HowTo 富媒体搜索结果；不要以 `FAQPage`、`HowTo` 或 AI 引用为理由添加标记。
- 结构化数据只在当前受支持、真实适用且与可见内容一致时实现；它提供机器可读线索并可创造功能资格，但不保证排名或生成式 AI 展示。

## 七、发布、实验与复盘

每个被采纳问题写入内容 brief：证据、目标市场、页面任务、答案负责人、所需一手资料、实施 QA、主指标、护栏与停止条件。

复盘顺序：

1. 验证内容、内链、canonical 和测量在真实渲染结果中正确；
2. 确认搜索系统已有机会抓取和索引变更；
3. 在同一页面、查询类别、国家、设备和品牌口径下观察 GSC 查询组合、展示与合格点击；
4. 对比处理 cohort 与可比页面/改动前趋势，并记录 SERP 变化；
5. 在自然落地页、市场和时间 cohort 层面观察合格转化与销售结果；
6. PAA/AI 归属只通过带日期的重复样本报告，不用单次出现宣称“赢得”功能。

检查频率和观察窗口由该站抓取延迟、数据量、业务周期与预先定义的最小有意义效果决定。采用 `references/review-engine.md` 的结论状态；低样本或无法控制干扰时标 `directional` 或 `inconclusive`。

## 八、可选能力与 fallback

| 需要 | 可选能力 | fallback |
|---|---|---|
| PAA/AI/SERP 样本 | `seo-dataforseo` | 在目标市场用浏览器或用户截图进行有限人工采样，注明非穷尽 |
| GSC 需求 | `seo-google` | 请求页面/查询/国家/设备导出；缺失时不声称已有自然需求 |
| 页面抓取/竞品覆盖 | `seo-firecrawl` | 浏览器/curl 读取有限 URL，保存日期、范围和引用 |
| 关键词估算 | Keyword Planner/专业数据源 | 使用 CRM、RFQ、站内搜索和 PAA 作为定性措辞证据，不编搜索量/KD |
| 业务结果 | GA4/CRM | 请求自然落地页 cohort 导出；不可得时只评价实施与搜索领先信号 |

能力调用前先检查是否存在。不可用时执行 fallback 并标记未知项，绝不虚构问题、SERP、搜索量、排名、引用或转化。

## 九、追踪格式

```markdown
| Question/task | Market | Source/date | First-party validation | Existing URL |
| Gap type | Decision | Why/evidence | Owner | Deploy date |
| Artifact QA | Search evidence | Business evidence | Verdict | Next signal |
```

记录到 content/keyword tracker 与 `.vibio/changelog.md`，保留历史观察。PAA 退出、措辞变化或生成式回答变化都可能是 SERP 波动，不自动意味着内容失败。
