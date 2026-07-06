# 关键词验证协议 — 目标市场真实搜索验证

回答一个问题：**这个词，目标国家的目标客户真的会搜吗？** 关键词研究的最大浪费不是漏词，是把资源投给"看起来相关、其实没人搜（或搜的人不是买家）"的词。本协议是 KEYWORD 引擎的强制闸门：每个候选词在进入词→页映射之前，必须过五道验证；验证不过的词，一票否决或降级，不管它"感觉多核心"。

核心判据：**关键词的合法性来自目标市场的真实搜索行为证据，不来自翻译、不来自老板的直觉、不来自同行网站的抄袭。**

---

## 一、为什么必须验证：直译陷阱

直译优化的是"意思对"，不是"搜索行为对"。搜索引擎排序看的是母语用户实际怎么措辞，不是语言学上是否正确。一个从中文直译的英文词可以读起来完全通顺，但真实买家从来不这么搜。

**典型症状**（出现任何一条就该怀疑选词）：页面读起来流畅、已被收录、内容也不差——但从不排名、没有点击、没有询盘。

| 中文思维直译（没人搜） | 买家真实用词（该做的词） |
|---|---|
| non-standard customization | custom fabrication / custom machining |
| factory direct sales | manufacturer / factory supplier |
| metal plate processing | sheet metal fabrication |
| fastening pieces | fasteners |
| profile section material | aluminum extrusion profiles |

**三条铁律：**
1. **别拿其他中国出口商的网站验证用词**——他们的词可能同样是直译出来的，这是循环引用 Chinglish。验证基准只能是目标国家的原生来源：本土竞品、行业媒体、买家社区、SERP 本身。
2. **会说英语不等于会选英文词。** 对中文关键词研究我们不会请翻译来做，对英文关键词研究同理——判断依据是搜索数据和母语语料，不是语感。
3. **每种语言独立选词，不做词表直译。** 中英文的 SERP、量、意图几乎不 1:1 对应（此规则与 `write-playbook.md` 阶段 9、`multi-language-ops.md` 一致）。

---

## 二、五道验证闸门

候选词依次过闸；任何一道明确失败即 FAIL（淘汰），证据不足即 CONDITIONAL（降级，标注待验证项）。

### Gate 1 — 母语性验证：这个措辞在母语来源里真实存在吗？

**执行机制**：默认工具是 `WebSearch`（搜候选词和 `site:` 限定查询，读结果标题/摘要判断）和 `WebFetch`（抓竞品页/论坛帖原文）；有 `seo-dataforseo` MCP 时用它拉真实 SERP 和 autocomplete 数据更准；有浏览器类 MCP 时可模拟目标国 locale。工具再少也能跑——用 WebSearch 的结果标题做母语性判断即可，但要在结论里注明数据来源层级。

**操作**：把候选词放进目标国家的原生语料里找证据。任选两个来源交叉确认：
- 目标国本土竞品/分销商的页面上出现过这个确切措辞（title、H1、类目名）
- Google Autocomplete（目标国 locale）能联想出这个词或其近似形式
- SERP 前 10 的 title 里有本土站点用这个措辞
- Reddit / 行业论坛 / PAA 里买家自然用过这个说法

**判定**：两个以上母语来源出现过 → 过。只在中国出口商网站上见过 → FAIL（直译陷阱）。查不到但业务上确信有需求 → 转零搜索量判定框架（见第五节）。

### Gate 2 — SERP 试金石：搜索结果页上的人群，是你的客户吗？

搜索量再高，SERP 人群不对就是错的词。Google 用多年点击数据早已给每个词定了性——读 SERP 就是读 Google 的意图判决。

**操作**：拉目标国口径的 SERP——首选 `seo-dataforseo` 的 location 参数（返回真实的分国 SERP）；无 MCP 时用 `WebSearch` 搜这个词并按结果的站点类型/标题判断页型（注意 WebSearch 不保证目标国 locale，判断时优先看结果里的本土域名和站点身份）；用户手工核对时给出无痕窗口 + `google.com?gl=us` / `google.co.uk?gl=uk` / `google.com.au?gl=au` 的操作说明。给前 10 名逐个标注页型。

**页型判读表：**

| SERP 主导页型 | 判定（假设你是 B2B 出口制造商） |
|---|---|
| 制造商/供应商官网、类目页、spec 表 PDF、行业媒体 | ✅ 对口，过闸 |
| 对比矩阵、"best X suppliers"、询价页 | ✅ 商业调研型，过闸（页型要匹配） |
| 消费者博客、DIY 教程、生活方式测评 | ❌ 人群错配，FAIL——量再大也别做 |
| 招聘网站、职业介绍 | ❌ 求职者的词，FAIL |
| 词典、百科、纯学术 | ⚠️ 纯信息型；目标钱页已存在或已列入路线图（即使未发布）才做，否则降级 |
| B2C 电商（Amazon 零售页） | ⚠️ 零售买家；除非做零售，否则 FAIL |

**SERP 特征作为意图代理**：精选摘要 + PAA 多 → 信息型；购物卡片/广告多 → 交易型；出现同行广告 → 商业价值被市场验证过（正信号）。**页型错配双向适用**：SERP 全是对比矩阵而你打算写长文，就是格式错配（详见 `seo-sxo`）。

### Gate 3 — 量与趋势的真实性：按目标国家口径，不看全球数

**操作**：
- 查**目标国家**的量，不是全球量。`seo-dataforseo` 用 `location_code`+`language_code`（不要 `location_name`+`language_code` 混用，会返回空值）；无 MCP 时走免费降级链（第七节）。
- Google Trends 看趋势方向和国别差异——用 **Topic 模式**而非 Search term 模式（Topic 自动合并拼写变体；"color" 和 "colour" 按纯文本查是两条曲线）。
- 检查季节性和衰减：一个连续两年下行的词不值得当支柱。

**判定**：目标国有量 → 过。工具显示 0 → 不是自动 FAIL，转零搜索量判定框架（第五节）。只有全球量、目标国没量 → FAIL 或换目标市场。

### Gate 4 — 搜索者身份排除：过滤"看着相关、其实不是买家"的词

同一个表面措辞可能同时服务买家、求职者、学生、DIY 爱好者。B2B 场景下这是询盘率杀手。

**否定信号表（词或其主要长尾里出现即扣分）：**

| 人群 | 信号词 |
|---|---|
| 求职者 | jobs / careers / salary / hiring / resume / intern |
| 学生/学术 | thesis / research paper / homework / course / for beginners / introduction to |
| DIY 消费者 | DIY / how to make / homemade / at home / craft |
| 免费党 | free / open source / free forever（若你无免费层） |
| 零售散客（对批发商而言） | used / cheap / for sale near me / 单件零售修饰词 |

**注意**：信号词按精确短语判断，别一刀切——"research on carbon fiber suppliers" 是真买家在做采购调研，"carbon fiber research paper" 是学生。拿不准就回 Gate 2 看 SERP 上排的是谁。

### Gate 5 — 商业路径：这个搜索者能变成客户吗？

**操作**：给词标注买家旅程位置（认知/评估/决策），并回答"搜这个词的人，到询盘/下单还差几步"。
- 决策层词（supplier / manufacturer / custom / bulk / quote / price per unit + 规格词）→ 优先级最高
- 评估层词（vs / best / specifications / how to choose）→ 做，承接到钱页
- 认知层词（what is X）→ 只在能喂内链、建主题权威时做，且要接受 AI Overview 会吃掉大部分点击（见第六节）
- 与业务转化无路径的词（纯好奇、纯学术）→ FAIL

---

## 三、买家用语挖掘工具箱（按信号强度排序）

选词不是坐着扩词，是去买家真实说话的地方抄词。优先级从高到低：

1. **一手询盘 / RFQ 原文（最高信号，免费，独家）** — 问客户/销售：询盘邮件、RFQ 表单、展会名片背面，买家用什么词描述要买的东西？每个高频问题 = 一个信息词；每个高频异议 = 一个对比/决策词。这是竞品拿不到的语料。
2. **GSC 已有查询挖掘** — Performance → Queries：已经给你带来曝光的词是被 Google 验证过的真实查询。注意：GSC 会隐藏大量长尾（Queries 表只显示部分；Pages 曝光总量远大于 Queries 归因总量属正常），用 API 拉可到 5 万行。
3. **母语竞品页面挖掘** — 拉目标国本土竞品（不是其他出口商）的高流量页，抄它们的类目命名、规格措辞、title 用词。有 `seo-dataforseo` 就拉它们的 ranked keywords。
4. **Google Autocomplete（目标国 locale）** — 种子词 + a-z / 数字 / 修饰词（for, with, vs, price, supplier）逐个联想；递归展开（把联想结果再喂回去）。这是实时真实查询流。
5. **PAA / AlsoAsked** — 真实问题的树状分支，直接反映买家自然措辞；问题词进 FAQ 和 H3。
6. **Reddit / 行业论坛** — `site:reddit.com` + 行业词；工程类：r/AskEngineers、r/manufacturing、Eng-Tips.com。买家在被营销话术污染之前如何描述问题，这里最真实。
7. **B2B 平台搜索联想** — Thomasnet（北美工业买家，措辞偏技术：材料牌号、公差、认证）、Alibaba RFQ（措辞偏价格量级）。两边语料代表买委会里不同角色。
8. **评论与职位描述挖掘** — G2/Amazon 评论里的用户原话；LinkedIn 上买方角色（Procurement Manager / Sourcing Engineer）职位描述里的高频措辞。

**买委会视角**：制造业采购是委员会决策——质量工程师搜 "tensile strength ASTM A36"，采购搜 "steel plate bulk pricing"，生产搜 "steel plate supplier lead time"。把词映射到具体角色，内容才能覆盖整个买委会。

---

## 四、地区变体核对（同一个概念，各国不同词）

同一产品概念在 US/UK/AU 的主导措辞、拼写、单位都可能不同，搜索量被拆散在各变体上。做哪个市场就用哪个市场的变体，别混用。

| 维度 | US | UK / AU | 对策 |
|---|---|---|---|
| 拼写 | aluminum / customized / color / fiber | aluminium / customised / colour / fibre | 每个核心词各查一遍变体量 |
| 用词 | wrench / truck / gas | spanner / lorry / petrol | 用本土竞品页面确认主导词 |
| 单位进查询 | "6 inch pipe" / Fahrenheit | "150mm pipe" / Celsius | 规格类词按目标市场单位出变体 |

**分国家查量方法**：① Google Trends「Compare → Change filters → 每条曲线设不同国家」看相对差异（Topic 模式合并变体）；② `seo-dataforseo` 用数字 `location_code`（如 2840=US）逐国查绝对量；③ Keyword Planner 免费版分国家定向也能给区间。工具间绝对数不一致属正常，跨国相对比较才可信。城市级搜索量任何主流工具都给不出，国家/州是实用下限。

---

## 五、零搜索量词判定框架（B2B 特有）

工具显示 0 量 ≠ 没人搜。关键词工具依赖 clickstream 面板数据，系统性漏掉企业网络、隐私意识强的专业用户、和高度技术化的措辞——恰好是工程师和采购的画像。**含标准号/认证/材料牌号/公差/精确规格的词，工具 0 量应读作"未测量"，不是"不存在"。**

**采信证据（有任意一条即可当真实需求对待）：**
1. GSC 里这个词（或近似词）过去 3-12 个月有曝光
2. 它出现在 PAA / AlsoAsked / Autocomplete 里（Google 自己观测到过这个查询）
3. SERP 上有专门服务这个词的商业页面（别人已经在赚这个词的钱）
4. 询盘 / CRM / 站内搜索里出现过买家原话

**聚合逻辑**：单个 0 量长尾不单独建页（`keyword-engine.md` 既有规则），但 30 个各约 10 次真实搜索的长尾聚合到一个深度页/簇上，合格流量常超过一个 300 量的泛词。**按商业接近度加权，不按量加权**：一个 0 量但对应 5 万美元订单的规格词，价值高于 5 万量的消费者泛词。

---

## 六、AI 搜索时代的选词修正（2025-2026）

- **目标单位从"单个词"变成"意图簇"。** AI Mode / AI Overviews 用 query fan-out 把一个查询拆成多个并行子查询再合成答案。业界研究显示：能覆盖主词 + ≥1 个 fan-out 子查询的页面，被 AI Overview 引用的概率约高 161%；被引用页约 68% 不在传统 top-10（具体数值随行业与查询类型波动，方向参考）。选词时就用 PAA/AlsoAsked 把子问题面圈出来，一个页面规划覆盖整簇。
- **B2B 商业词相对抗零点击。** AI Overview 触发集中在信息型查询（约 88%），零点击冲击主要吃掉 "what is X" 类流量；买家要询价/比供应商仍必须点出去——**验证协议默认偏向的商业意图 + 规格词，恰好是抗 AI 侵蚀的资产**。信息型词照做（喂权威、争引用），但流量预期要按零点击时代打折。
- **会话式长查询占比上升**（AI Mode 查询比传统搜索长 2-3 倍）——问题形长尾和自然语言措辞的权重在验证时上调。
- 不要拿工具导出的 fan-out 子查询列表当字面词表用——它们不稳定（重复查询仅约 27% 一致），当方向信号用。

---

## 七、免费数据降级链（无 MCP / 付费工具时按序使用）

| 顺位 | 来源 | 可信度 | 用法 |
|---|---|---|---|
| 1 | GSC（自有站） | 最高（第一方真实数据） | Queries 报表 / API 拉长尾；已有曝光=已验证 |
| 2 | Bing Webmaster Tools | 高 | 第二个第一方来源 + 免费 Keyword Research 工具 |
| 3 | Google Autocomplete | 高（实时需求，无量级） | 目标国 locale + a-z/修饰词递归展开 |
| 4 | Google Trends | 中（仅相对/趋势） | Topic 模式、分国对比、判生死不判大小 |
| 5 | Keyword Planner 免费档 | 中（对数区间） | 分国家定向；10/100/1K-10K 区间粗排 |
| 6 | SERP 计数（`allintitle:` / 引号精确匹配） | 低（竞争密度代理） | allintitle 结果数低 + 意图明确 = 可能的低竞争机会 |

前提条件注意：顺位 1/2 需要站点已验证（GSC/Bing WMT 权限），顺位 5 需要 Google Ads 账号——新站没有这些时降级链实际可用的是 3/4/6 三项。用了降级链要在输出里如实标注"估计，依据 X"——这条与 `keyword-engine.md` 的"不编数字"铁律一致。

**最坏情况兜底**：若全链不可用（无账号、无 MCP、WebSearch 也受限），明确告知用户"当前无法验证搜索量与母语性，以下判断仅基于业务逻辑推断，标注 unverified，需接入数据源后复核"——不得跳过标注直接给出验证结论。

---

## 八、验证评分卡（写回 tracker 的格式）

每个候选词过完五道闸门后打标：

| 判定 | 条件 | 处置 |
|---|---|---|
| **PASS** | 五道全过，有母语证据 + SERP 对口 | 进入词→页映射，正常排优先级 |
| **CONDITIONAL** | Gate 1/3 证据不足（如 0 量待验证），但 Gate 2/4/5 通过 | 可做，但不做支柱页；随长尾聚合投产，GSC 出数后复核——复核结果（证实/证伪）按 `learning-loop.md` 回流经验库，这是本协议自我校准的数据源 |
| **FAIL** | 任意一道明确失败（直译无证据 / SERP 人群错 / 身份排除命中 / 无商业路径） | 淘汰。记录失败原因防止下次再提 |

写回 `.vibio/trackers/keywords.md` 时使用 `Validated` 列（`pass` / `conditional` / `fail-淘汰不入表`），`Notes` 里记一句证据（如 "US SERP 全是 supplier 页 + autocomplete 有"）。字段见 `state-templates.md`。

---

## 九、与现有模式的集成

| 模式 / 文件 | 接入点 |
|---|---|
| **KEYWORD 模式**（`keyword-engine.md`） | 扩展候选集之后、可操作性打分之前，全量过五道闸门；Validated 列写回 tracker |
| **WRITE 模式**（`write-playbook.md` 阶段 0a/1） | 自主选词时推荐清单只允许 PASS 词；用户指定的词若未验证，先跑本协议再动笔 |
| **PLAN 模式**（`operating-system.md` Week 2） | 关键词架构周的产出物必须带 Validated 标注 |
| **多语言**（`multi-language-ops.md`） | 每种语言独立跑本协议，禁止词表直译 |
| **数据源** | `seo-dataforseo`（分国量/SERP）、`seo-google`（GSC 挖掘）、`seo-sxo`（SERP 页型深读） |

---

## 不要做

- 不拿中文词直译当英文关键词——先过母语性闸门。
- 不拿其他中国出口商的网站当用词证据——循环引用 Chinglish。
- 不看全球搜索量做目标国决策——量必须按目标国家口径。
- 不把工具 0 量直接当"没人搜"淘汰——含规格/标准/牌号的词先走零搜索量判定框架。
- 不跳过 SERP 试金石就凭量选词——SERP 人群错配的词，量越大浪费越大。
- 不给验证不过的词建页——FAIL 的词记录原因归档，防止复活。
- 不把 AI fan-out 子查询列表当字面词表——当方向信号。
- 不在无数据时编造搜索量——用降级链并标注"估计"。
