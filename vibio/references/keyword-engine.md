# Keyword Engine — 查询族到页面架构

本引擎是 `vibio-keyword` 的共享方法。目标是建立经目标市场证据验证、能服务真实买家任务、各有主页面和业务路径的查询族架构，而不是输出一串第三方工具关键词。

## 执行流程

1. **续接状态**：读取 `.vibio/` 的业务、市场、页面和关键词历史；没有则建立最小上下文。
2. **建立种子任务**：从产品/服务、RFQ/CRM、GSC、站内搜索、paid search terms、销售异议和现有页面提取产品、规格、应用、采购、选型、标准与排错任务。
3. **扩展候选**：按 `keyword-validation.md` 的来源优先级扩展。第三方工具只提供其口径下的估算；记录国家、语言、日期与限制。
4. **验证目标市场**：执行母语/买家表达、SERP 人群与页型、地区需求、搜索者身份、商业路径五道闸门，标 `pass / conditional / fail`。
5. **决定投资顺序**：根据商业价值、需求证据、意图/页型、信息增益、当前立足点、成本依赖和可测性，按 `authority-cascade.md` 标 `now / next / later / reject`。KD 只作带来源的辅助证据，不使用固定 phase。
6. **词族到页面**：一个买家任务/查询族指定一个主页面，标 `existing / new / merge / expand / reject`；暴露 cannibalization。
7. **形成任务网络**：商业页与规格、应用、选型、案例和支持内容按用户任务相连；不为同义词或 query fan-out 变体机械建页。
8. **写回与交付**：更新 keyword tracker，保留历史；交付验证证据、页面映射、优先顺序、数据限制和下一步。

## 能力路由

- `keyword-validation.md`：验证闸门、零量判断与降级链；
- `paid-search-intelligence.md`：将广告 search terms、Keyword Planner 和线索质量用于 SEO 学习；
- `seo-dataforseo`：可选的第三方地区需求、SERP、趋势和竞品数据；
- `seo-google`：可选的 GSC 查询/页面数据；
- `seo-sxo`：SERP 意图与页型深读；
- `seo-cluster`：可观察 SERP 重叠辅助分簇；
- `seo-competitor-pages`：竞争页面任务与缺口；
- `seo-content-brief` / `vibio-content`：下游大纲与成稿。

外部能力缺失时走 manifest fallback；没有数据就标未知，不编搜索量、难度或排名周期。

## 交付字段

```markdown
| Query family | Market/language | Buyer/task | Intent | Validation |
| Owner page | Page decision | Investment | Demand source |
| Difficulty evidence | Current signal | Decision note | Checked at |
```

## 不要做

- 不拿直译、全球量、Ads competition/CPC 或第三方 KD 当目标市场自然需求/难度真值。
- 不把工具 0 量自动判为无需求或高价值。
- 不用“打得过”代替真实 SERP 缺口、站内立足点和信息增益。
- 不为每个长尾、同义词或 AI fan-out 变体建页。
- 不交付没有验证、页面归属、优先级、数据来源与限制的关键词清单。
