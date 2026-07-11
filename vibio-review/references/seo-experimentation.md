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
