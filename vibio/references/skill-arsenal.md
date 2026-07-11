# 外部能力清单

Vibio 可使用以下 27 个外部专项能力。本文只负责**按需路由并整合结果**，不是要求每次全部调用，也不重新手写其完整分析。

使用规则：
- 将当前决策需要的能力匹配到下方 Skill；独立且确有必要的能力可并行。
- 若依赖的 MCP/API 不可用，说明缺口并按 manifest 降级到源码、渲染产物、用户导出或有边界的人工检查。
- 能力返回后，将发现整合进按证据和影响排序的结果，不直接转发原始 dump。
- 所有分数、搜索量、难度、毒性标签、建议和能力声明仍需证据审查。下列描述只用于路由，不能覆盖 `evidence-policy.md`、实时官方文档或 manifest fallback。

## 第一层：编排与策略

### seo
面向各种站点/业务的综合 SEO 分析入口，可协调全站审计、单页、技术、结构化数据、内容、图片、sitemap 与 AI 搜索。当需求很宽且需要一个总协调能力时使用。

### seo-audit
配置允许时执行抓取并委派专项审计。用户提出 audit、full SEO check、analyze my site、website health check 时可用。抓取上限和 health score 只是工具设置，不是 SEO 真相；保留样本覆盖并自行按已验证发现排序。

### seo-plan
为新站或现有站制定 SEO 策略与实施路线。用户提出 SEO plan/strategy、keyword strategy、content calendar 时可用，但输出必须经过 Vibio 的项目证据与产能约束。

### b2b-seo
B2B/SaaS 策略能力，覆盖 B2B 关键词、买家任务内容、企业 SEO 与内容规划。它是外贸制造/B2B 的优先候选能力，但不能跳过技术、测量、目标市场和需求验证。

## 第二层：页面与内容

### seo-page
深度分析单页的 on-page 元素、内容质量、技术 metadata、结构化数据、图片和性能。用户要求 analyze this page 或 check this URL 时可用。

### seo-content
分析内容质量、经验/专业/权威/可信框架、可读性和薄内容。除非目标平台与站点的明确实验已验证，否则忽略 proprietary AI-citation-readiness 分数。

### seo-content-brief
生成竞品内容简报、页面任务结构、证据需求和页型模板。用户只要 content brief、outline、blog brief 时使用。字数只是编辑预算；丢弃固定关键词密度或“比竞品稍长”的处方。

### seo-cluster
基于实际 SERP 重叠而非文本相似度做主题聚类，并设计 hub-and-spoke 与内链矩阵。用户提出 topic clusters、content architecture、pillar pages 时可用。

### seo-programmatic
面向数据驱动批量页面的 programmatic SEO，覆盖模板、URL、内链自动化、薄内容防护与索引膨胀。用户提出 programmatic SEO、pages at scale、dynamic pages 时可用。

### seo-competitor-pages
生成 X vs Y、alternatives、功能矩阵和比较页。Google 没有通用 comparison schema；只有可见页面独立符合当前支持类型时才添加结构化数据。

## 第三层：技术与结构化数据

### seo-technical
审计可抓取性、可索引性、安全、URL、移动端、Core Web Vitals、结构化数据和 JS 渲染。IndexNow 只对明确支持它的搜索引擎可选，不能当 Google 索引修复。

### seo-schema
检测、验证和生成 Schema.org 结构化数据（优先 JSON-LD）。只验证与可见内容一致、目标使用方当前支持的类型。Google FAQPage/HowTo 富结果已退役；结构化数据资格不是排名或 AI 展示承诺。

### seo-sitemap
分析或生成 XML sitemap，并验证格式、URL 和结构。用户提出 sitemap、generate sitemap、sitemap issues 时可用。

### seo-hreflang
审计、验证和生成 hreflang/国际 SEO 实现，检查回链、语言/地区代码、canonical 与索引资格。

### seo-images
优化图片的 alt、体积、格式、响应式输出、懒加载、CLS、图片搜索资格和 WebP/AVIF；IPTC/XMP 只按真实需求采用。

### seo-image-gen
只生成明确披露的非事实性插画、OG/社交预览和解释图。不得合成产品摄影、工厂/流程/测试证据、认证、客户结果或案例证明；事实性主张必须使用真实资产。生成图只有在真实代表可见页面且符合目标功能当前规则时，才可被结构化数据引用。

## 第四层：AI 搜索

### seo-geo
分析 AI Overviews、AI Mode、ChatGPT web search、Perplexity、Bing Copilot 的证据与可见性。平台主张须对照实时官方文档。对 Google，正常 SEO 资格和非同质化内容是基础；`llms.txt`、特殊 AI schema 与任意 citability 分数都不是 Google 要求。

### seo-flow
FLOW（Find -> Leverage -> Optimize -> Win）证据型框架。只在用户明确需要该框架时调用，阶段提示不能覆盖 Vibio 证据政策。

### seo-sxo
从 SERP 反推页型/意图错配并以多角色审视页面，用于诊断 why isn't this ranking、page-type mismatch、search intent mismatch。其 persona score 只是分析工具，不是排名事实。

## 第五层：外部数据（多数需要 MCP/API）

### seo-google
访问 Search Console（Search Analytics、URL Inspection、Sitemaps）、PageSpeed Insights、CrUX 与 GA4 organic 数据。站点上线并验证后，这通常是高价值一方证据。Google Indexing API 不是通用 URL 提交工具，只限受支持的 JobPosting 或直播 BroadcastEvent 页面。

### seo-dataforseo
通过 DataForSEO MCP 获取 SERP 样本、关键词估算、趋势、外链、on-page、竞品/内容与商家数据。保留 provider、地区、语言、设备、日期和方法；搜索量、难度、意图与外链指标是估算，不是 Google 一方真值。

### seo-backlinks
分析引用域、锚文本上下文、疑似垃圾模式与竞品差距。重要链接需人工核验；provider 的 toxic 标签本身不足以支持 disavow。

### seo-firecrawl
通过 Firecrawl MCP 做全站抓取、提取和映射。记录抓取范围与失败 URL，不能把有限抓取称为全站完整。

## 第六层：本地与电商（纯 B2B 外贸通常跳过）

### seo-local
本地 SEO：Google Business Profile、NAP 一致性、引用、评论、本地结构化数据、地点页与多门店。适用于实体门店、服务区域或混合业务。

### seo-maps
地图情报：geo-grid、GBP API 审计、评论、跨平台 NAP、竞品半径与 LocalBusiness 标记。第三方网格/评分保留时间、地点和采样边界。

### seo-ecommerce
电商 SEO：Shopping 可见性、商城情报、Product 标记、价格与 marketplace 查询差距。用户提出 ecommerce SEO、shopping、product schema at scale 时可用。

## 第七层：监控

### seo-drift
保存 SEO 关键元素基线、检测漂移和回归。适用于改版、迁移后或用户提出 SEO drift、baseline、did anything break、SEO regression。

## 路由模式

- **线上站点宽泛审计**：用 `seo-audit` 协调，或只并行调用当前决策必需的专项能力。
- **代码库 SEO 审查**：先读 `seo-fix-principles.md` 并识别技术栈，再用 `seo-schema` 验证受支持 JSON-LD、用 `seo-technical` 检查抓取/索引逻辑。
- **新 B2B 项目**：先验证业务结果、技术/索引资格、测量、目标市场语言、需求、意图和页面所有权；再仅为已验证的下一决策调用 `b2b-seo`、`seo-content-brief` 或 `seo-cluster`。
- **无流量/不排名**：`seo-google` 检查索引与一方数据 -> `seo-sxo` 检查意图/页型 -> `seo-content` 检查任务完成与证据。
- **AI 搜索可见性**：`seo-geo` + 当前平台文档，使用带日期的平台专项证据；`llms.txt` 只有目标平台记录支持时才可选，绝不是 Google 要求。
- **上线后监控**：风险、变化速度、数据成熟度或待决策事项需要时，用 `seo-drift` 基线 + `seo-google` 复盘；不因日历到期重复抓取。
