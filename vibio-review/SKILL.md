---
name: vibio-review
description: >-
  当用户问“之前的 SEO 改动见效了吗”“复盘排名/流量/询盘”“月度 SEO review”“did these SEO changes work”“compare SEO before and after”时使用。本 Skill 从确切变更、日期与基线出发，先确认产物未回归，再结合 GSC、分析平台和 CRM 的适当粒度判断实施失败、尚不可观察、方向性改善、增量改善、未检测到变化、负向/回归或证据不足，并给出下一步。默认中文；seo-google、seo-drift 等能力可选，缺失时按 manifest fallback。不用于首次审计、直接修复或无历史基线的排名承诺。
compatibility: 最佳输入是变更日志、渲染基线、GSC/分析/CRM 导出和预先约定的指标。缺失数据时仍可做产物复核，但必须降低结论强度。
---

# Vibio SEO REVIEW

默认用中文复盘；目标市场中的 query、页面和实验素材保留原语言。

REVIEW 回答的是“什么证据足以改变下一步”，不是把同期变化强行归因给 SEO。必须把产物是否持续存在、搜索系统是否响应、用户行为和业务结果分层判断。

## 必读资料

- `references/evidence-policy.md`：证据等级、数值与测量边界。
- `references/roi-attribution.md`：GSC、分析平台和 CRM 的可连接粒度。
- `references/seo-experimentation.md`：对照、观察窗口、混杂因素和停止规则。
- `references/google-search-docs.md`：指标与 Google 产品行为；易变事项复盘前核验实时文档。
- `references/capability-routing.md`：数据能力不可用时的降级方案。
- `references/state-templates.md`：项目状态和变更日志格式。

## 工作流

### 1. 重建决策记录

读取 `.vibio/project.md`、`changelog.md` 和相关 tracker；没有状态文件时，从 Git、部署记录、CMS 历史或用户材料重建最小基线。对每个待复盘改动确认：

```text
Change and affected pages:
Implemented on:
Artifact verification at launch:
Expected mechanism:
Primary outcome metric:
Guardrails:
Baseline / comparison unit:
Observation window and stop rule:
Known concurrent changes:
```

缺少变更日期、范围、基线或指标时，可以做状态审查，但不得给出确定的因果结论。

### 2. 检查能力与数据覆盖

`seo-google`、`seo-drift`、`seo-dataforseo` 等仅在实际可用时调用：

- GSC/GA4/CRM 可用：记录 property、过滤条件、日期、时区、覆盖率和匿名/隐藏数据限制。
- 只有导出：验证字段定义和同口径窗口后分析。
- 没有外部数据：比较当前 HTTP/渲染产物与保存基线，说明只能证明“变更仍存在/已回归”，不能判断流量或收入效果。

始终执行 manifest 中的 fallback，不生成缺失的排名、流量、索引或转化数据。

### 3. 先验证产物

在评估结果前确认变更仍然存在：状态码、canonical、robots、title/snippet 输入、渲染主内容、内链、hreflang、sitemap 和受支持的结构化数据。部署回归或标签未渲染时，优先判为 `implementation-failed` 或 `negative-or-regression`，不要拿搜索结果评价一个实际上未生效的 treatment。

### 4. 分层读取结果

按变更机制选择指标，不为所有改动套同一 KPI：

1. **资格层**：抓取、Google 选择的 canonical、索引状态、受支持搜索展示资格。
2. **可见性层**：GSC 的页面/query class/国家/设备维度展示、点击、CTR、平均排名与 search appearance。
3. **站内层**：分析平台中的 organic landing sessions、任务完成和事件质量。
4. **业务层**：按 landing page、市场、日期 cohort 或意图簇观察合格线索、商机、成交和淘汰原因。

GSC 测量访问前，分析平台测量页面加载后的行为，两者不会完全一致。只能按 landing page、country、device、date 等共享聚合维度关联；不得把某条 GSC query 确定性连接到某个 GA4 用户、转化或收入。Query 级收入模型必须标注为估算并披露假设。

### 5. 选择合理比较

优先采用 `references/seo-experimentation.md` 中当前可行的最强设计：随机/匹配页面组、带对照的时间序列或可回滚测试。至少处理：

- 品牌词与非品牌词、页面类型、国家/语言和设备 mix。
- 季节性、促销、迁移、核心更新、竞争变化及同期内容/链接/模板改动。
- 数据延迟、抓取频率、样本量、长销售周期和未成熟 cohort。

观察窗口和最小有意义效果必须由项目自身基线、抓取情况、方差和业务周期确定。不存在通用的“2-6 周”、固定 impression 门槛、固定 CTR 曲线或统一 uplift 标准。数据不足时标记 `inconclusive`，不要用行业平均值填空。

### 6. 给出判定

| 判定 | 使用条件 |
|---|---|
| `implementation-failed` | 目标改动未进入或未保留在真实产物中 |
| `not-yet-observable` | 预设窗口尚未成熟，或抓取/销售周期尚未覆盖 |
| `directional-positive` | 相关指标改善，但样本或设计不足以支持因果 |
| `incremental-positive` | 合格对照、分阶段 rollout 或可信中断时间序列与业务指标共同支持反事实增量 |
| `no-detectable-change` | 在预设的充分窗口与检测能力内，没有达到最小有意义效果 |
| `negative-or-regression` | 目标或预设 guardrail 明确恶化，且实施/干扰已检查 |
| `inconclusive` | 覆盖不足、噪声过大、混杂无法排除或指标定义失效 |

对每个判定写明 effect size/方向、不确定性、证据等级和适用范围。不要把平均排名的一次波动、单条 query 或单日截图升级为结论。

### 7. 形成下一步

```text
Decision:
Evidence and limitations:
Keep / expand / revise / rollback / continue to maturity:
Exact next action:
Owner and dependency:
Next metric, window and stop condition:
```

- 回归或产物失败：转 FIX。
- 新的根因未知：转 AUDIT。
- 主瓶颈已解决：转 PLAN，重排资源。
- 数据不足：先修测量或继续到预设成熟点，不承诺“再等就会涨”。

按 `references/state-templates.md` 追加 REVIEW 结论，保留数据范围、置信度和下一窗口；不要覆写历史。如果要跨项目沉淀经验，必须取得用户授权并按 `references/learning-loop.md` 匿名化，单个观察不得升级为普遍规则。

## 付费搜索边界

付费搜索词、paid & organic report 或受控落地页实验可以帮助判断买家用语、意图、信息表达和额外需求信号，但广告不会提升自然排名。Paid & organic report 只形成覆盖、蚕食或增量假设；只有合格对照设计才能估计因果增量。只把付费结果反馈到明确的 SEO 决策，不接管 Campaign、出价或预算运营。

## 不要做

- 不使用固定 CTR、转化率、排名位次、样本门槛或生效周期判成败。
- 不把前后同期变化自动称为 SEO 导致。
- 不把 Schema 存在或 AI 平台的一次引用当作排名效果证明。
- 不做确定性的 GSC query 到 GA4/CRM conversion 连接。
- 不在数据能力缺失时伪造 provider 输出。
