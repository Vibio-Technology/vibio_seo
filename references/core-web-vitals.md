# Core Web Vitals 审计与验证基线

最后核验：2026-07-11。Core Web Vitals（CWV）产品行为会变化；行动前重新核对实时官方文档，并记录工具、采集窗口、设备和 URL/源站粒度。

## 官方来源

- Google Search 的 CWV 说明：https://developers.google.com/search/docs/appearance/core-web-vitals
- 指标与阈值：https://web.dev/articles/vitals
- 阈值制定方法：https://web.dev/articles/defining-core-web-vitals-thresholds
- Chrome UX Report API 与 28 天窗口：https://developer.chrome.com/docs/crux/api
- CrUX 方法：https://developer.chrome.com/docs/crux/methodology
- INP 的 field/lab 测量边界：https://web.dev/articles/inp
- Lighthouse Total Blocking Time：https://developer.chrome.com/docs/lighthouse/performance/lighthouse-total-blocking-time

## 判定口径

使用真实用户页面加载的第 75 百分位（p75）判断每项指标。推荐阈值对移动与桌面相同，但应分别查看移动端和桌面端数据，不能用混合设备汇总掩盖其中一端的问题。

| 指标 | Good | Needs improvement | Poor |
|---|---:|---:|---:|
| LCP | `<= 2.5 s` | `> 2.5 s` 且 `<= 4.0 s` | `> 4.0 s` |
| INP | `<= 200 ms` | `> 200 ms` 且 `<= 500 ms` | `> 500 ms` |
| CLS | `<= 0.1` | `> 0.1` 且 `<= 0.25` | `> 0.25` |

不要把平均值、最佳一次测试、Lighthouse Performance 分数或某个首页结果替代 p75。一个站点也不能因三项中的一项良好就被描述为“通过 CWV”；逐项、逐设备、逐粒度报告。

CWV 是 Google 搜索系统使用的页面体验信号之一，但相关性和影响范围有限。达到阈值不保证收录、排名、展示或流量增长；未达到阈值也不能自动解释全部自然搜索变化。

## Field-first 证据顺序

1. 优先使用项目自己的 RUM，或 PageSpeed Insights/CrUX 的真实用户数据判断线上结果。
2. 先取 URL 级数据；URL 样本不足时可查看 origin 级数据，但必须标明粒度降级，不能把源站汇总归给单页。
3. 分开查看 `PHONE` 与 `DESKTOP`。CrUX API 未传 `formFactor` 时会聚合所有设备，该结果不能替代设备级判断。
4. 没有 CrUX 数据通常表示样本或收录资格不足，不表示页面良好、糟糕或“0 ms”。输出 `insufficient-field-data`，再用 RUM 或实验室诊断补充。
5. 记录 `collectionPeriod.firstDate`、`collectionPeriod.endDate`、采集工具、URL/origin、设备和指标 p75。

CrUX API 是过去 28 天的滚动聚合，通常还存在约两天处理延迟。`collectionPeriod` 即使显示 28 天，也不保证新页面拥有完整 28 天样本。因此：

- 部署次日的 CrUX 变化不能归因给本次修复；
- 相邻日期查询的大部分样本重叠，不能当作两组独立观测；
- 做前后对比时使用成熟、口径一致的窗口，并记录同期发布、流量结构和设备结构变化；
- 项目 RUM 可作为更快的方向性信号，但仍需固定页面组、设备、版本和统计口径。

## Lab 诊断边界

Lighthouse 和 DevTools 用于复现、定位和回归，不用于证明真实用户 p75 已改善。

- Lighthouse 是特定设备、网络、页面状态和单次运行下的实验室测量；缓存、地理位置、扩展、第三方脚本和运行波动都会改变结果。保存配置并重复运行。
- Lighthouse 的 TBT 统计 FCP 到 TTI 之间长任务的阻塞部分。它可帮助诊断加载阶段主线程阻塞，也可能作为 INP 的合理代理，但不是 INP 本身。
- INP 取决于真实交互。只加载页面、不执行交互的实验室工具不能覆盖整段访问中的交互；人工或自动交互测试得到的 lab INP 也只代表已执行的流程。
- TBT 下降、Lighthouse 分数上升或一次 lab INP 通过，只能写成“实验室回归改善”，不能写成“CWV 已通过”。

## 修复与复核流程

1. 定位受影响的模板、页面组、设备和指标，不用站点平均值隐藏长尾。
2. 从 field 数据确定问题，再用 trace、Lighthouse、性能面板和可复现交互寻找原因。
3. 设定业务与体验 guardrail，例如转化、错误率、图片质量、可访问性和关键功能，不为分数破坏页面。
4. 部署后先验证产物、错误和 lab 回归；再用 RUM 观察版本化 cohort。
5. 等待 CrUX 窗口成熟后复核相同 URL/origin 与设备口径。将结果写成 `improved`、`regressed`、`no-detectable-change` 或 `insufficient-data`，不要承诺排名变化。

## 输出记录

```text
URL/template group:
Device: phone | desktop
Field source: CrUX URL | CrUX origin | RUM
Collection period:
Metric and p75:
Status: good | needs-improvement | poor | insufficient-field-data
Lab setup and repetitions:
Observed bottleneck:
Change and artifact verification:
Guardrails:
Post-release RUM result:
Mature CrUX review date:
Search/business outcome: pending | directional | experiment-supported
```
