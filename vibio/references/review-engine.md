# Review Engine — SEO 增量复盘

本引擎回答三件事：改动是否真的上线、搜索系统是否已经有机会观察到它、业务结果是否出现可信变化。它不使用固定“涨 3 位”“点击 +20%”或“六周没涨就失败”的通用阈值。

## 一、先建立可复盘对象

读取 `.vibio/project.md`、`.vibio/changelog.md` 和相关 tracker。每个改动至少需要：

- 改动日期与实际部署日期；
- 受影响 URL / 模板 / 国家 / 语言；
- 改动前后规格或快照；
- 预期机制，例如“解除 noindex”“改善查询承诺”“增加相关发现入口”；
- 主指标、护栏指标和预定观察窗口；
- 同期迁移、改版、促销、季节性或算法波动等干扰。

没有这些记录时，先重建最小基线。无法重建就标 `no-comparable-baseline`，不要把相关变化归因给某次改动。

## 二、分四层复测

### 1. 实施层

在真实渲染结果中确认改动仍存在：状态码、robots 指令、canonical、标题、主内容、结构化数据、内链、hreflang、资源加载和分析标记。使用 `seo-drift` 时要保留本地降级：直接抓取、解析并与保存快照比较。

如果部署未生效或已回归，结论是 `implementation-failed`，直接转 `vibio-fix`；此时没有资格评价 SEO 效果。

### 2. 抓取与索引层

按改动机制检查：

- GSC URL Inspection 的索引状态、Google-selected canonical、最近抓取等可用字段；
- sitemap、内部入口和实际响应；
- 目标国家页面是否可发现，hreflang/canonical 是否互相冲突；
- 页面是否出现在相关 GSC 页面/查询数据中。

Google 不保证固定重抓时间。不要把“两周/六周”写成全站规则；根据该站同类 URL 的历史抓取延迟、URL Inspection 状态和实际曝光判断是否已经有可观察机会。

### 3. 搜索表现层

优先用 GSC，并保持比较口径一致：

- 页面、查询、国家、设备、搜索类型和品牌/非品牌过滤一致；
- 对齐相同星期结构与相近长度，季节性业务优先同比或用对照 cohort；
- 同时看 clicks、impressions、CTR、position 的分布与查询组合，不用单个平均排名下结论；
- 检查查询是否更贴近目标买家，而不是只看总曝光；
- 记录 GSC 查询匿名化、聚合和数据延迟限制。

GSC 与 GA4 的口径不同，数据不会精确相等。GSC 不能把匿名查询确定性连接到 GA4 转化；业务复盘应在自然落地页、页面组、国家和时间 cohort 层面进行。

### 4. 业务层

使用 GA4、CRM、订单、询盘质量、电话或销售反馈，观察：

- 合格自然会话和目标落地页参与；
- 表单/电话/试用/订单等主转化；
- 合格线索率、成交或贡献价值；
- 线索的国家、产品和意图是否符合目标。

广告 search terms 可帮助解释买家语言和落地页转化，但不得把广告点击或 Ads 转化记成 SEO 增量。细则见 `references/paid-search-intelligence.md` 和 `references/roi-attribution.md`。

## 三、比较设计

### 最佳：分批上线或对照 cohort

对同类页面随机或分批处理，保留未处理的可比组。比较处理组与对照组的变化差异，避免把季节、品牌活动或全站更新误认成单页改动效果。

### 次佳：中断时间序列

没有对照组时，保留足够长的改动前趋势，标注发布点并检查趋势/水平变化。重大站点改版、算法更新和促销期间要降低因果置信度。

### 最低：前后窗口

只能前后比时，选择可比窗口并展示原始分母。小样本只报告方向，不做统计显著承诺。实验方法见 `references/seo-experimentation.md`。

## 四、结论状态

| 状态 | 证据要求 | 下一步 |
|---|---|---|
| `implementation-failed` | 改动未上线、回归或测量损坏 | 转 `vibio-fix`，修复后重启观察 |
| `not-yet-observable` | 已上线，但抓取/收录或数据成熟度不足 | 设下一检查点，并说明等待什么信号 |
| `directional-positive` | 相关领先/业务指标改善，但样本或设计不足以支持因果 | 继续观察或扩大受控样本 |
| `incremental-positive` | 合格对照、分阶段 rollout 或可信中断时间序列与业务指标共同支持反事实增量 | 保留改动，按已验证的同类适用范围扩展 |
| `no-detectable-change` | 数据量足够，观察窗口与设计合理，未检测到有意义变化 | 检查机制、意图与信息增益，决定停止或重做 |
| `negative-or-regression` | 搜索或业务护栏恶化，且实施/干扰已检查 | 回滚可逆改动或转审计定位 |
| `inconclusive` | 基线缺失、干扰过多、口径不一致或数据不足 | 修复测量，不能宣称成功/失败 |

“有意义变化”的最小幅度必须由业务价值、历史波动和实验前约定决定。不得事后挑一个刚好成功的百分比。

## 五、按改动类型选择指标

| 改动 | 先看 | 再看 | 不应期待 |
|---|---|---|---|
| noindex/canonical/状态码修复 | 实施、抓取、索引 | 相关曝光与业务访问 | 立刻提升所有排名 |
| 标题/snippet 改写 | 新标题是否被采用、查询/设备分层 CTR | 合格点击与转化 | Google 必然采用所写标题/描述 |
| 内容与意图重构 | 相关查询组合、曝光、页面参与 | 合格线索/收入 | 单靠字数产生排名 |
| 内链 | 发现路径、抓取、相关入口 | 目标页查询与业务表现 | 固定链接数对应固定名次 |
| 结构化数据 | 语法/资格/增强结果状态 | 对应搜索展示和点击 | 通用排名或 AI 引用提升 |
| CWV/性能 | CrUX 字段数据和技术护栏 | 同 cohort 搜索/业务结果 | Lighthouse 单次分数等于排名变化 |
| OG/社交分享 | 社交抓取与分享展示 | 社交引荐表现 | Google 自然排名提升 |

## 六、无外部能力时的降级

- `seo-google` 不可用：请求用户导出的 GSC/GA4 文件；仍不可得时只做实施与公开可抓取信号复测。
- `seo-drift` 不可用：保存当前 HTML/关键字段，与 `.vibio/` 基线做结构化 diff。
- `seo-dataforseo` 不可用：不编排名；GSC 已有数据优先，必要时做带日期/地区的有限 SERP 人工抽样。
- CRM 不可用：明确只能评估搜索领先指标，不能评价收入增量。

## 七、写回格式

```markdown
## REVIEW — YYYY-MM-DD
- Change ID / URLs:
- Comparison design:
- Observation window:
- Implementation: pass / failed
- Crawl/index evidence:
- Search evidence:
- Business evidence:
- Confounders and limitations:
- Verdict: implementation-failed / not-yet-observable / directional-positive /
  incremental-positive / no-detectable-change / negative-or-regression / inconclusive
- Decision: keep / expand / revise / rollback / wait
- Next check and required signal:
```

更新 keyword/content/link tracker 时保留旧值和日期，不能覆盖掉历史。跨项目经验只记录会改变未来决策、且已去标识化的结论；一次方向性变化不能升级成通用规则。

## 八、官方口径

- Search Console Performance 报告与数据差异：https://support.google.com/webmasters/answer/7576553
- Search Analytics API 数据限制：https://developers.google.com/webmaster-tools/v1/how-tos/search_analytics
- URL Inspection API：https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- Google Analytics 归因说明：https://support.google.com/analytics/answer/10596866
- Google 搜索实验的现实限制由项目数据决定；具体设计见 `references/seo-experimentation.md`。

## 九、不要做

- 不在确认实施与可观察性之前评价效果。
- 不用固定重抓周期、CTR 曲线、排名位次或增长百分比判所有项目。
- 不把平均排名当成一个稳定的单关键词名次。
- 不把 GSC 查询和 GA4 用户/转化做确定性连接。
- 不只报总流量，忽略国家、意图、页型和线索质量。
- 不把同期品牌、广告、PR、季节或改版影响归功于 SEO 改动。
- 不把“数据不足”包装成“需要再等一等”；要说明缺什么数据、何时能判断。
- 不覆盖历史 tracker，也不挑成功案例做选择性复盘。
