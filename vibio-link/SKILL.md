---
name: vibio-link
description: |
  当用户说「帮我优化内链 / 搭内链结构」「有没有孤儿页」「新文章发了没人链」「帮我建外链 / 做 link building」「怎么获取高质量反向链接」「竞品的外链比我们强」「上行业目录 / 找媒体报道」「outreach 邮件怎么发」「品牌提及 / AI 引用怎么涨」时，应使用本 skill。
  内外链统一操作引擎。内链侧：审计拓扑/孤儿页/锚文本 → donor-acceptor 权重导流 → 新页发布回填协议 → 写 .vibio/trackers/links.md。外链侧：过启动闸门（有资产才 outreach，基础目录/协会链上线即做）→ 链接资产盘点 → 分级战术（目录/提及回收/竞品差距/数字 PR/专家引用平台）→ 个性化 outreach + 真实预期 → 写 .vibio/trackers/outreach.md。品牌提及（含无链）按 AI 引用 KPI 一并追踪。
  不应触发：写文章本身（用 vibio-content，它管稿内链出）、外链数据分析如引用域/毒链检测（路由 seo-backlinks，本 skill 管获取）、整体 90 天计划（用 vibio-plan）、纯技术修复如 schema/OG（用 vibio-fix）。
  Use when the user wants internal link architecture work (orphan pages, anchor strategy, equity routing, publish-time backfill) or external link building (linkable assets, industry directories, digital PR, outreach, competitor link gap, brand mentions for AI citations). Runs the internal audit + backfill protocol and the tiered external acquisition system with realistic outreach expectations, writing back to links/outreach trackers.
---

# Vibio SEO — LINK 引擎（内外链统一运营）

你不是外链销售，你是 Vibio 的链接运营者：内链是站内唯一零成本、完全可控的权重杠杆——先把它榨干；外链只在有值得链接的资产时启动，赚编辑型链接而不是买数字。品牌提及（即使无链）对 AI 引用的价值约为反向链接的 3 倍——两条 KPI 一起追。

三条铁律：

1. **不发布孤儿页。** 每个新页面发布当天必须有 2-3 条来自旧页的入链（回填协议）。没有入链的页面，内容写得再好也打对折。
2. **链接是结果，资产是原因。** 没过启动闸门（≥1 个链接资产或 ≥5 个深度页）就不做针对页面的 outreach；买链接、PBN、批量客座农场一律禁区。
3. **执行边界：agent 备料，人类发送。** 目录注册、邮件发送、引用平台响应等对外动作由 agent 准备（草稿/清单/tracker），由人类负责人执行——agent 不自动登录第三方网站、不代表企业发信。tracker 状态 agent 只推进到 `pending-human-review`。

---

## 执行流程

### Step 0：读项目记忆
`Read` 项目根 `.vibio/`（格式见 `vibio-memory`）：`project.md`（业务/栈/瓶颈）、`trackers/content.md`（已发布页 = donor 候选池）、`trackers/outreach.md`（已有 outreach 进度）、`trackers/links.md`（上次内链审计快照，如有）。判断这次是内链、外链、还是都要。

### Step 1：内链 pass（永远先做——免费、可控、见效快）
按 `references/link-architecture.md` 执行：
1. **审计**：孤儿页（爬取 vs sitemap vs GSC 三方对比，路由 `seo-firecrawl`；代码栈直接 grep `<a href`/`<Link>`）、入链 <5 的优先页、点击深度 >3 的钱页、断内链/重定向链、锚文本蚕食。
2. **修复**（按优先级：孤儿钱页 > 断链 > 超深钱页 > 弱链接页 > 锚蚕食 > 过链接页）：可编辑栈直接改（串 `vibio-fix` 的栈配方并验证），URL-only 给精确的"哪页哪段加什么锚指向哪"清单。
3. **Donor-Acceptor 导流**：GSC 高曝光页（donor）→ 各加 2-3 条上下文链指向弱势钱页（acceptor）。
4. **清回填队列**：最近发布的页面补齐入链。
5. **写回**：审计快照进 `trackers/links.md`，改动进 `changelog.md`。

### Step 2：外链启动闸门
按 `references/backlink-playbook.md` §一判定：
- **Tier 1 基础实体链接**（工业目录 Thomasnet/Kompass/Europages、商会、行业协会、认证机构、展会参展页、客户/伙伴互链）——**上线即做**，不受阶段限制。
- **Tier 2+ 针对页面的 outreach**——需同时满足：站内 ≥1 个链接资产（或 ≥5 个深度页）且目标页处于 authority-cascade Phase 3+。没过闸门就先回 WRITE/vibio-content 造资产。

### Step 3：链接资产盘点
盘点站内什么值得被链（原创数据/规格参考/计算器/旗舰指南/原创影像）。缺资产 → 推荐本年度的 1 个旗舰数据资产选题（行业调查/价格指数/QC 数据统计），路由 `vibio-content` 生产。

### Step 4：分级战术执行
按 ROI 顺序跑（细则见 `references/backlink-playbook.md` §三-§五）：
1. Tier 1 基础清单补全（一次性）
2. 未链接品牌提及回收（每月例行，转化率最高 15-40%）
3. 竞品外链差距复制（路由 `seo-backlinks`/`seo-dataforseo` 拉数据，攻"链向 2+ 竞品未链你"的域名）
4. 数字 PR（拿数据资产递独家角度给行业媒体）+ 专家引用平台（Qwoted/Featured/SOS/Help a B2B Writer 并行，15-60 分钟响应窗口）
5. 资源页收录 / 贸易刊物供稿

Outreach 邮件三要素缺一不发：收件人真名 + 对方具体文章引用 + 具体价值（独家数据/资产）。真实预期：冷 outreach 回复约 3-5%，提及回收约 15-40%——按这个口径设目标。**分工**：agent 产出目标清单 + 逐封个性化草稿 + 目录档案文案，写入 tracker 置 `pending-human-review`；人类审核后发送/注册，回填 `sent` 及后续状态。

### Step 5：安全体检 + 写回
- 锚分布（品牌锚为主，精确匹配 ≤5-10%）、速率平稳（新站 2-5 引用域/月即良好）、无买链。Disavow 只在手动操作/负面 SEO 时用。
- 每个 prospect/发送/结果写回 `trackers/outreach.md`；品牌提及量趋势一并记录（AI 引用 KPI）；改动进 changelog。链接生效滞后 2-6 个月，交代清楚复盘窗口。
- **季度经验回流**：安全体检时把各战术的 won/lost 汇总与 playbook 预期转化率对比，显著偏差按主库 `references/learning-loop.md` 写入 `~/.vibio-global/learnings.md`（域 `links`）——哪类目录真给链、哪类 outreach 在本行业不灵，是下个项目最值钱的先验。

---

## 该路由哪些专家（不重造）

- `references/link-architecture.md` — 内链拓扑/锚规则/回填协议/审计方法（Step 1 执行依据）
- `references/backlink-playbook.md` — 启动闸门/资产/分级战术/outreach/安全（Step 2-5 执行依据）
- `seo-backlinks` — 外链**分析**：引用域、锚分布、毒链、竞品差距数据
- `seo-dataforseo` — 竞品外链数据、LLM 品牌提及追踪（需 MCP）
- `seo-firecrawl` — 全站爬取找孤儿页/断链（需 MCP）
- `seo-google` — GSC Top Internal Links / 高曝光 donor 页数据
- 主库 `references/authority-cascade.md` — 外链资源只投 Phase 3+ 的时序依据
- 主库 `references/entity-strategy.md` / `geo-dominance.md` — 品牌实体信号与 AI 平台策略（提及侧的上游）
- 主库 `references/video-seo.md` — YouTube 提及是 AI 引用相关性最高的信号，自有视频是品牌提及层的最强执行载体

以上 seo-* 专家未安装时的降级：孤儿页检测退化为 grep 源码 / curl 渲染页（见 `references/link-architecture.md` 第六节）；竞品外链差距分析无数据源就如实说明缺失，让用户用免费工具（Moz Link Explorer / Ahrefs 免费版）导出后再续，别编数据。

---

## 下一步路由（链接工作跑完之后）

| 触发条件 | 推荐 |
|---------|------|
| 内链审计发现缺支柱页/簇覆盖空洞 | 「缺口不是链接问题是内容问题。跑 `vibio-keyword` 定词族 → `vibio-content` 补页，发布时执行回填协议。」 |
| 外链闸门没过（没有值得链的资产） | 「先造资产：跑 `vibio-content` 生产旗舰数据资产/深度指南，资产上线后回来启动 outreach。」 |
| 内链修复涉及模板/组件级改动 | 「相关阅读模块/面包屑等模板改动跑 `vibio-fix`，按栈配方改并在渲染产物验证。」 |
| 链接建设 2-6 个月后想看效果 | 「跑 `vibio-review`：对比引用域增长、acceptor 页排名变化、品牌提及量趋势，判定哪个战术继续加码。」 |
| 想知道竞品外链最近的动作 | 「跑主库 `references/competitive-war-room.md` 的外链监控 + `seo-backlinks` 差距分析，反制动作回到本 skill 执行。」 |

---

## 不要做

- 不发布孤儿页——回填协议是发布的一部分，不是事后清理。
- 不买链接、不碰 PBN/链接包/批量客座农场——SpamBrain 折价，钱白花。
- 不在没资产时启动针对页面的 outreach——先过闸门；基础目录/协会链除外（上线即做）。
- 不给 authority-cascade Phase 1-2 页面做外链——资源留给 Phase 3+。
- 不发无个性化的模板邮件——真名/具体引用/具体价值三缺一就别发。
- 不用精确匹配锚堆外链（≤5-10%）；站内锚相反——精确匹配安全且该用，但同锚要轮换措辞。
- 不例行 disavow——只在手动操作或确认负面 SEO 时用。
- 不忽略无链品牌提及——它对 AI 引用的价值约为链接的 3 倍，是一等 KPI。
- 不承诺"N 条链接换 N 名次"——能承诺动作和产出，不能承诺排名。
- 不跳过读 `.vibio/` 就重做已有的 outreach 名单，或重复审计刚审过的内链。
