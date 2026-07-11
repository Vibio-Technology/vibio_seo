# SEO 业务测量与归因

最近核验：2026-07-11。

目标是把搜索工作连接到合格业务结果，同时拒绝数据无法支持的伪精确归因。

官方来源：

- GSC + GA4：https://developers.google.com/search/docs/monitor-debug/google-analytics-search-console
- GA4 当前归因模型：https://support.google.com/analytics/answer/10596866
- GA4 推荐 lead events：https://developers.google.com/analytics/devguides/collection/ga4/reference/events

## 测量边界

GSC 测量访问前的 Google Search 展示与点击；Analytics 测量页面成功加载后的站内行为。两套数字设计上就不会完全一致。

不能把某条 GSC query 与某个 GA4 用户或转化做确定性连接。只在 landing page、country、device、date 等共享聚合维度上结合。Query 级收入/CPA 只能是模型，必须标为估算。

## Event 与 CRM 设计

按业务类型追踪真实结果：

- 电商：`view_item`、`add_to_cart`、`begin_checkout`、`purchase`，并在可用时加入利润/退货。
- SaaS/服务：trial、demo/request、qualified opportunity、订阅或成交收入。
- B2B/制造：询盘、样品/RFQ、合格线索、销售跟进/接受、商机、成交、淘汰。

GA4 推荐的线索生命周期事件包括 `generate_lead`、`qualify_lead`、`working_lead`、`close_convert_lead`、`disqualify_lead`。在隐私和同意边界内，让网站标识与 CRM 阶段衔接，不能只停在表单提交数。

记录：

- Landing page 与页面/意图簇。
- 可用的 source/medium/campaign。
- 市场、语言、设备和日期 cohort。
- 线索阶段变化与淘汰原因。
- 合适场景下的收入、毛利或合格 pipeline value。
- 跟踪覆盖率和隐私限制。

## GA4 当前归因模型

只使用目标 property/报告当前实际提供的模型。核验时官方选项包括 data-driven attribution、paid and organic last click、Google paid channels last click。

First-click、linear、position-based、time-decay 已不是 GA4 当前原生选项。只有作为自建离线分析模型，且明确假设、数据和敏感性时才能使用。

归因只是分配 credit 的模型，不证明渠道导致了结果；需要因果置信时做增量实验。

## 默认报告粒度

### Landing page 与意图簇

这是 SEO 业务分析的默认粒度：它能把聚合的 Search 可见性连接到站内/CRM 结果，而不虚构用户级 query join。

```text
页面/意图簇 | 市场 | organic clicks | 合格访问 | 新线索 |
合格线索 | 商机 | 成交收入 | 成本 | 覆盖限制
```

### 品牌词与非品牌词

用 GSC query 分类分析展示/点击趋势，但不把精确收入绑到每条 query。对比 landing page 和 cohort 结果，并披露匿名/隐藏 query 的覆盖缺口。

### 长销售周期 cohort

按首次观察到的 organic landing 时间/页面簇分组，跟踪真实阶段变化。成熟和未成熟 cohort 分开报告，不能套统一 lag factor。

```text
Cohort | 页面簇 | 新线索 | 合格 | 商机 | 成交 |
到达各阶段中位天数 | 已观察收入 | 成熟度/覆盖率
```

## 计算

只使用项目实测输入，保留完整漏斗，不乘行业默认值：

```text
合格线索率 = 合格线索 / 符合条件的 organic landing sessions
商机率 = 商机 / 合格线索
成交率 = 成交 / 已成熟商机
已观察 organic cohort value = 定义 cohort 内已成交收入总和
已观察 cohort 单位成本 = SEO 项目实测成本 / 该 cohort 的合格线索
已观察 cohort 净值 = 该 cohort 已观察毛利 - 实测生产/维护/分发成本
```

以上是描述性单位经济，不证明这些线索或毛利由 SEO 增量造成，也不能命名为“SEO 贡献毛利”或增量 ROI。只有使用合格对照、分阶段 rollout、可信中断时间序列或其他能估计反事实的设计，才报告增量线索、增量利润或增量 ROI，并披露假设与不确定性。

收入尚未成熟时，用企业自身历史阶段转化率展示 pipeline 与情景范围。预测、假设和敏感性必须标明，不能称为已实现或增量 ROI。

## 付费搜索对照与实验

Google Ads 可以提供目标市场 search terms、paid & organic 描述性合并报告，以及消息/落地页实验。合并报告只能观察覆盖重叠和组合指标，增量/蚕食因果需要另行设计对照；广告不会提升自然排名。

在页面/意图簇或市场 cohort 层，以一致的合格线索与收入定义比较 SEO 和 Paid Search。不能拿估算的关键词级 organic CPA 与精确 paid CPA 当作同口径实测值。

验证闭环见 `paid-search-intelligence.md`。

## 决策报告

在数据达到预设成熟度或出现需要决策的变化时报告；不因固定月历重复尚未变化的数据。只报告会改变行动的指标：

1. 主瓶颈及其是否变化。
2. 搜索资格与 index coverage。
3. 按页面簇/市场的非品牌可见性和合格 landing 流量。
4. 新线索 -> 合格 -> 商机 -> 成交漏斗。
5. 哪些页面/实验属于 `not-yet-observable`、`directional-positive`、`incremental-positive`、`no-detectable-change`、`negative-or-regression` 或 `inconclusive`。
6. 已用成本/产能与下一步资源分配。
7. 数据覆盖、归因限制和未验证假设。

## 数据缺失

全漏斗数据不可用时：

1. 明确缺少哪个字段、阻断什么决策。
2. 使用最接近的实测 proxy，但不能改称收入。
3. 补齐下一阶段的埋点。
4. 只向用户索取最小必要 CRM/export 数据。
5. 不用通用转化率、成交率、内容寿命、CTR 曲线或 lag multiplier 填空。
