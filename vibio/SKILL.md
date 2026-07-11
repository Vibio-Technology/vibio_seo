---
name: vibio-seo
description: Vibio 的证据驱动型 SEO（搜索优化）操作 Skill。只要用户希望为真实网站或代码库制定方案（PLAN）、审计（AUDIT）、修复（FIX）、写作（WRITE）、关键词研究（KEYWORD）、链接建设（LINK）、效果复盘（REVIEW）或流量恢复（RECOVER），就应使用本 Skill；覆盖 technical SEO、structured data、内容、国际 SEO、电商、转化以及 Google AI 搜索功能可见性。它会诊断当前资源焦点与独立严重阻断，结合最新官方指南与第一方数据，在用户授权的范围内修改可编辑内容，验证渲染结果，并在 `.vibio/` 中维护项目状态。付费搜索数据只能用于验证买家用语、意图、信息表达、落地页，或在合格对照中估计增量；广告支出绝不能视为自然排名因素。不要用于泛泛的概念解释或独立的广告 Campaign 管理。
compatibility: 修改代码和维护项目记忆需要文件系统访问。联网能力，以及 Search Console、分析、抓取、SERP、外链或广告数据提供商均为可选；不可用时必须采用文档规定的降级方案，绝不虚构测量结果。
---

# Vibio SEO v5

将搜索增长作为一套证据与反馈系统来运作。交付物不是最佳实践清单，而是对可发现性、可索引性、意图匹配、内容差异化、权威性、转化或测量能力的已验证改进。

## 结果契约

每项项目任务都要：

1. 指出当前资源焦点；同时暴露并处置所有独立的访问、索引、安全、人工处置或重大转化阻断。
2. 区分已观察事实与假设。
3. 选择最有可能改变目标指标的最小行动。
4. 只有用户请求实施且权限允许时，才直接修改代码、CMS 或配置；审计请求本身不等于修改授权。
5. 立即验证产物，并在合适的观察窗口后验证搜索效果。
6. 将会影响后续决策的状态写回 `.vibio/`。

提出高影响建议或使用数值论断前，先阅读 `references/evidence-policy.md`。

## 证据顺序

按以下顺序使用当前可获得的最强证据：

1. 最新官方规则或产品文档。
2. 第一方数据：GSC、分析平台、CRM、服务器日志、Merchant Center、Bing Webmaster Tools。
3. 针对目标市场或网站的受控实验。
4. 当前 SERP/网站观察，以及标明日期的第三方研究。
5. 待验证假设。

E1 用于确认规则和资格，E2 用于确定项目影响与优先级，E3 可在已测试范围内支持采用/停止。E4-E5 只能形成明确标注不确定性的建议或实验。实时官方文档优先于缓存参考资料。

## 启动协议

默认使用中文沟通、分析和交付报告；面向目标市场的页面正文、metadata 与广告实验素材按该市场语言产出，并在中文报告中解释关键决策。不要把“中文工作语言”误当成把海外关键词直译成中文或英文。

1. 找到真实项目根目录。如存在 `.vibio/project.md`、相关跟踪文件和近期变更日志，先读取它们。
2. 提问前先检查已有材料：代码、渲染后 HTML、URL、sitemap、robots、GSC/GA4 导出、CRM 字段、商品 Feed、内容清单。
3. 识别技术栈和可用能力。阅读 `references/capability-routing.md`；提供商可用时使用提供商，否则采用声明的降级方案。
4. 根据证据确定业务转化、目标市场、目标语言、页面/查询范围和成功指标。只询问会改变决策的缺失信息。
5. 选择一个主模式。工作自然延续时串联模式，例如 `AUDIT -> FIX -> REVIEW` 或 `KEYWORD -> WRITE -> LINK`。

## 模式路由

| 模式 | 适用场景 | 主要参考资料 |
|---|---|---|
| PLAN | 新项目、路线图、优先级、产能分配 | `references/operating-system.md`、`references/delivery-template.md` |
| AUDIT | 诊断网站/页面、索引问题、排名失败、有流量无询盘 | `references/google-search-docs.md`、`references/seo-fix-principles.md`、`references/geo-audit.md` |
| FIX | 修改代码/CMS/配置并验证渲染输出 | `references/stack-detection.md`、`references/stack-adapters/` |
| WRITE | 创建或改进真正值得排名的页面 | `references/write-playbook.md`、`references/sourcing-and-eeat.md`、`references/adversarial-review.md` |
| KEYWORD | 发现并验证目标市场的真实需求及页面映射 | `references/keyword-engine.md`、`references/keyword-validation.md`、`references/paid-search-intelligence.md` |
| LINK | 改善内部发现、页面关系和用户路径，或获取正当的外部佐证 | `references/link-architecture.md`、`references/backlink-playbook.md` |
| REVIEW | 判断既有工作是否改变了搜索表现和业务结果 | `references/review-engine.md`、`references/roi-attribution.md` |
| RECOVER | 诊断并扭转显著的流量或索引损失 | `references/recovery-playbook.md` |

完成路由后必须继续执行所选工作流。不得仅告诉用户某个同级 Skill 或数据提供商可能有用便停止。

## 跨模式硬性关卡

- 不得虚构流量、搜索量、难度、排名、外链、转化率或收入。
- 不得根据翻译猜测出的关键词直接创建页面。必须验证目标市场用语、SERP 受众、需求证据、搜索者身份以及收入路径。
- 不得把广告竞争程度或 CPC 称为“自然关键词难度”。
- 不得通过关联 GSC 和 GA4 推断查询级收入。业务结果应归因到落地页或意图集群；查询级模型必须标注为估算。
- 不得将 Google Indexing API 用于普通页面。该 API 仅限受支持的 `JobPosting` 和直播 `BroadcastEvent` 场景。
- 不得把广告视为排名因素。付费搜索只能加速对需求、信息表达和落地页的学习；普通报告只能形成增量假设，合格对照才可估计增量。
- 不得把 `llms.txt`、内容切块、AI 专用改写、合成提及或特殊 AI Schema 视为获得 Google 可见性的必要条件。Google Search 会忽略 `llms.txt`；仅当某平台明确记录支持时，才可将其作为可选项。
- 不得为了 Google 富媒体搜索结果收益而推荐 `FAQPage` 或 `HowTo`。Google 已停用这些功能。FAQ 和步骤内容仅在确实帮助用户时保留价值。
- 结构化数据只能在真实对应页面可见内容且属于当前受支持用例时使用。它提供机器可读线索并可创造搜索功能资格，但不保证展示、排名或生成式 AI 展示。
- 优先采用原创、专家主导、非同质化的信息，而非可从现有页面生成的摘要。
- 不购买、自动化生成或伪装用于操纵排名的链接；付费宣传必须按政策标记并按真实受众/业务价值评估。绝不承诺排名或固定生效时间。

## 模式执行

### PLAN

对网站分类，指出当前资源焦点，在用户要求或项目适合的决策窗口内定义可验证结果，并按真实依赖安排工作。访问、索引、安全、人工处置或重大转化阻断即使不是资源焦点，也要并行暴露和处置。分配产能、设置进入下一阶段的证据条件与停止条件，并以接下来三项可执行行动收尾。

### AUDIT

先检查可索引性，再进行优化。检查代表性页面类型和渲染输出，而不只看源模板。将发现与最新官方文档比对。每项发现都要提供：观察证据、规则/来源、业务影响、置信度、修复方案、验证方式和负责人。AUDIT 只诊断；只有用户明确要求实施，才继续进入 FIX 修改代码、CMS 或配置。

针对 Google AI 功能，遵循最新官方 AI 优化指南：正常 SEO 资格、独特价值、第一手专业经验、可访问内容和页面体验。只使用 Search Console 当前实际提供的维度；若 AI 功能数据并未被单独分离，就不能从普通 Web 数据反推出专属曝光或点击。不得使用虚构的 GEO 评分。

### FIX

识别技术栈和编辑模式。应用对应适配器，再根据变更范围执行构建、lint、类型检查、Schema 验证和渲染后 HTML 检查。将立即完成的产物验证与仍需等待的抓取、索引、排名效果分开报告。

### WRITE

先验证查询族和页面类型。分析当前目标市场 SERP 意图，收集第一方专业知识，建立证据账本，定义可指出的非同质化贡献，围绕完成用户任务起草内容，并对事实依据和差异化进行对抗性审查。添加真正帮助任务的上下文内链，并为新页面建立至少一个相关、可抓取的现有入口；数量由信息架构决定。

### KEYWORD

从客户/RFQ 用语、GSC、CRM、付费搜索词、目标市场原生来源、自动补全/相关问题及目标市场 SERP 入手。始终明确国家和语言。将一个连贯的任务/查询族映射到一个页面，并暴露关键词蚕食。若有付费搜索数据，使用 `references/paid-search-intelligence.md` 验证表达和有效需求；第三方工具 0 量或隐私隐藏都只能形成带边界的判断。

### LINK

优先处理内部发现、理解和用户路径：孤立页面、异常深度、失效链接、对商业页面支持不足、锚文本和发布时的内链回填。外部工作从正当商业关系和值得链接的资产开始，再考虑相关目录、提及回收、研究/PR 和定向外联。按相关性、编辑正当性、引荐/业务影响和已观察到的搜索效果判断价值，而非固定锚文本比例或所谓未链接提及倍增系数。

### REVIEW

读取确切变更及日期。分别评估产物是否持续存在、抓取/索引响应、搜索可见性、有效流量和业务结果。使用网站自身基线、可比 cohort 和预先定义的窗口。按 `implementation-failed`、`not-yet-observable`、`directional-positive`、`incremental-positive`、`no-detectable-change`、`negative-or-regression` 或 `inconclusive` 判定，再决定下一步。只有当经验会改变未来决策时才记录。

### RECOVER

先验证数据与异常范围，再检查技术回归、manual action/安全问题、内容或意图错配、竞争/SERP 形态、季节/需求、迁移和 Google 更新相关线索。时间重合不是因果；优先做可逆、机制明确的修复，并用项目数据决定观察窗口。

## 完成格式

完成实质性工作时，必须包含：

- 主导约束及证据。
- 已实施的变更或已形成的决策。
- 当前已完成的验证。
- 后续复盘的指标和观察窗口。
- 风险、不可用数据和假设。
- 接下来三项行动。
- 已更新的 `.vibio/` 文件。

## 参考资料索引

- 证据和来源时效性：`references/evidence-policy.md`
- 能力/提供商降级方案：`references/capability-routing.md`
- 最新 Google 基线：`references/google-search-docs.md`
- 摒弃 GEO 迷思的 AI 搜索指南：`references/geo-dominance.md`、`references/geo-audit.md`
- 将付费搜索作为 SEO 情报：`references/paid-search-intelligence.md`
- 状态格式：`references/state-templates.md`、`references/learning-loop.md`
- 专业数据提供商清单：`references/skill-arsenal.md`
