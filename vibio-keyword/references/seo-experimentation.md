# SEO 实验框架

实验用于降低不确定性，不能用噪声很大的前后对比制造确定感。

## 1. 先定义决策

```text
要做的决策：
主指标：
分析单元：页面 | 页面组 | query class | 市场
总体与纳入条件：
Treatment：
Control/对照：
预期机制：
最小有意义效果：
Guardrails：
起止时间与停止规则：
需监控的混杂因素：
Analysis timezone / temporal grain：
Source kinds / source timezones / metric mapping：
Data finality、分页、采样、阈值与归因模型验收条件：
```

结果不会改变行动的测试不要启动。

## 2. 证据设计

选择可行范围内最强的设计：

1. **随机页面组实验**：把足够相似的页面随机分到 treatment/control。适合有大量同类模板页的站点。
2. **匹配页面组**：按基线展示、排名、意图、市场与季节性配对，再只改变一组。
3. **中断时间序列**：建立稳定 pre-period，比较变更后的偏离，并尽量加入未变更页面/市场作为对照。
4. **Switchback/rollback**：对可逆呈现改动，在考虑抓取延迟后按计划切换或回滚。
5. **付费搜索实验**：在 organic exposure 成熟前验证措辞、意图、消息和落地页转化；广告不能测试排名效果。

简单的“最近周期 vs 上一周期”只是监控证据，不自动构成因果实验。

## 3. 合适的测试

| 假设 | 单元/测量 | 关键 guardrail |
|---|---|---|
| 更准确的 title 提高合格 organic clicks | 匹配页面；结合 query mix 与 position 看 GSC clicks/CTR | Google 可能重写，抽查实际 SERP |
| 新内容更好完成买家任务 | 页面/组；非品牌展示、合格 landing、CRM 阶段 | 避免同时改链接和模板 |
| 内链改善发现与权重流动 | 匹配 acceptor 页；抓取/收录/GSC 趋势 | 记录 donor 页变化与季节性 |
| 支持的 schema 获得搜索展示 | 合格页面组；Rich Results/GSC appearance | 仅测试当前支持且真实的类型 |
| 性能优化改善用户结果 | CrUX/RUM + 转化/参与 | Lab 分数不能代替 field outcome |
| 合并页面减少 cannibalization | Query/page sets；selected canonical 与合并后可见性 | 保留重定向/内链与回滚表 |

不得测试已停止的 FAQPage 或 HowTo 富结果，也不能把 schema 当通用排名实验。

## 4. Title 与 snippet 实验

Google 对 title 和 meta description 没有固定字符上限。Treatment 应简洁、准确、独特，并适配可能的设备。除非实验本身就在测该模式，否则不强制主词前置、年份、数字、括号或固定长度。

记录：

- 提供的 title/description 与可见 H1。
- 代表性 query 实际显示的 title/snippet。
- Query mix、品牌词占比、国家/设备、展示、点击、CTR 与 position distribution。
- 同期其他页面/SERP 变化。

有条件时判断合格点击与下游行为，而不只看 CTR。

## 5. 内容实验

测试具体的新增价值，不测试泛化的“加深内容”或字数。可选 treatment：

- 原创产品测试数据。
- 真实 failure-mode 决策树。
- 公开比较标准的一手对比。
- 市场特定标准/兼容性证据。
- 更有用的媒体或交互式决策工具。

衡量是否获得目标 query/task 覆盖和合格结果；篇幅变长本身不是 treatment。

## 6. 统计纪律

- 预先定义值得行动的最小效果。
- 用站点自身基线率和方差估算 power/sample；不存在通用的 100/500/1000 impressions 门槛。
- 前后使用相同 query/page/market 定义。
- 报告 effect size 与 uncertainty，不只报 winner/loser。
- 把核心更新、需求变化、改版、迁移、促销和竞品事件列为混杂因素。
- 不能只因结果暂时为正就提前停止。
- 低 power 结果应标为 inconclusive，不能升格为规则。
- 实施前冻结 `analysis_timezone`、`temporal_grain`、source ID/kind/timezone、每个指标的唯一来源映射和 attribution model。分析 metadata 只能补充 `data_as_of`、finality/preliminary、row-limit/pagination、sampling、thresholding 与 data quality 等采集状态；不得新增来源、修改冻结字段，也不能把计划中缺失的合同事后补齐为 complete。
- 日粒度 panel 必须逐实验单位覆盖完整基线与观察窗口，且分析期基线均值必须与计划中冻结的逐页面基线摘要一致；每个窗口只给一个代表日或事后更换基线都不具备增量解读资格。观察结束日当天还不是成熟窗口；来源时区必须越过次日零点，且数据截止点不能在未来。
- 冻结计划要在实施前写入 change 的首条 planned 记录，绑定 experiment ID、plan 文件 SHA-256 与 plan hash。复盘时再补 plan 不能称为预注册。
- GSC 日数据、GA4 property 日数据和 CRM 日数据若日界不同，不能先按日期拼 panel 再计算 DiD。应先在各来源的显式窗口内聚合，或保留 timestamp 并统一到 analysis timezone 后构造 panel。
- 任何来源元数据缺失/冲突、preliminary、触限、分页不完整、采样或阈值处理都使实验结果为 `inconclusive`，即使 DiD、CI 与护栏表面通过也不能进入增量解读。

小流量 B2B 站应结合一方定性证据、paid search terms、GSC 方向和合格 pipeline，不伪装成大样本统计结论。

## 7. 安全边界

- 不做 cloaking，不向搜索引擎提供实质不同内容。
- 不为简单 A/B 创建可索引重复版本。
- Access blocker、canonical、迁移、重定向实验必须有回滚和监控。
- 学习目标明确时不要同时改变多个因果层。
- 保护实质贡献收入的页面，除非预期价值与回滚条件明确。

## 8. 实验日志

维护 `.vibio/experiments.md`：

```md
| ID | 决策 | 单元 | Treatment | Control | 开始 | 主指标 |
| 最小效果 | Result/CI | Guardrails | Verdict | Rollout/rollback |
```

Verdict：`adopt`、`reject`、`inconclusive`、`invalidated` 或 `continue to maturity`。

采用结果时必须说明测试范围。只有在明显不同的页面/市场重复成立，或得到更强证据支持后，才能提升为通用 playbook。

`eligible_incremental` 只是人工增量解读入口。`incremental-positive` 还需预注册方向、可信反事实与机制共同支持。`no-detectable-change` 要求正式报告 CI 包含 0、预注册 MDE 可转换到指标单位，且状态工具生成并重放一致的 detectability 证据按同一 alpha/MDE/标准误计算双侧正态近似 power >= 0.8；实施、覆盖、污染、guardrail 和测量完整性门禁也必须全部通过。

Schema 有效、报告内部自洽或重算文件 SHA-256 都不足以支持强状态。状态工具会绑定 panel、artifact report 与可选 measurement metadata，重跑分析并比较除 `analyzed_at` 外的整份报告；额外自定义因果字段直接拒绝。完整性门禁未通过时，这两个强状态一律不可用。
