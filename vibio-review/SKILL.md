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
- `references/core-web-vitals.md`：p75 字段数据、设备拆分、CrUX 28 天窗口与 lab/field 边界。
- `references/bing-webmaster-docs.md`：目标包含 Bing/IndexNow/AI Performance 时的证据边界。
- `references/capability-routing.md`：数据能力不可用时的降级方案。
- `references/state-templates.md`：项目状态和变更日志格式。

## 自带复盘工具

1. 用 `scripts/seo_inspect.py` 以与上线时相同的范围和参数复验产物；产物不存在时优先判 `implementation-failed`。
2. 用户提供 GSC UI CSV 时，用 `scripts/gsc_compare.py` 计算同口径窗口和 page/query/country/device cohort。查询值若含高置信邮箱、电话、有效身份证号或带身份上下文的稳定 ID，工具会在聚合前拒绝且不回显原值；先在来源系统排除或不可逆脱敏。两期 CSV 的维度不同会默认拒绝；只有确认总体口径可比时才使用 `--allow-unaligned-overall`，并保留警告。

```bash
python scripts/gsc_compare.py \
  --input gsc.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example.com --search-type web \
  --analysis-timezone Asia/Shanghai \
  --source-timezone America/Los_Angeles \
  --data-as-of 2026-07-05T12:00:00Z --finality final \
  --no-row-limit-hit --pagination-complete --data-quality complete \
  --filter-notes "country=DE; device=all" \
  --json-out .vibio/runs/gsc-review.json \
  --markdown-out .vibio/runs/gsc-review.md
```

工具会重算 CTR、按展示量加权 position、对零分母返回 null，并记录来源 hash；它只产出描述性变化，不具备因果归因资格，也不与 GA4/CRM 用户级拼接。`analysis_timezone` 是分析/决策时区；GSC 常规日数据的 `source_timezone` 默认并记录为 `America/Los_Angeles`，不能把已汇总的 GSC 日期直接当成 Asia/Shanghai 日界。property、搜索类型、数据截止、finality、分页/行数上限或质量声明不完整时，报告降级为 `inconclusive`。

用户提供的是 Search Console **生成式 AI 效果报告** CSV 时，不要交给要求 clicks 的普通 Web 工具；改用 `scripts/gsc_ai_compare.py`：

```bash
python scripts/gsc_ai_compare.py \
  --input gsc-ai.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example.com --filters "country=DE" \
  --data-as-of 2026-07-05T12:00:00Z --finality final \
  --completeness complete --no-row-limit-hit \
  --json-out .vibio/runs/gsc-ai-review.json \
  --markdown-out .vibio/runs/gsc-ai-review.md
```

该报告按 PT 日期且 UI 最多展示 1,000 行，只提供 page/country/device/date 的 impressions；它是普通 Web Performance 的非可加子集。不得把两者相加，也不得推断 query、click、CTR、citation、转化、排名或因果。`preliminary`、触及行数上限、完整性未知、过滤或粒度不一致时只能判 `inconclusive`。

同时提供 GSC page、GA4 landing page 与 CRM 聚合 CSV 时，改用 `scripts/measurement_review.py`。配置必须显式声明两个窗口、`analysis_timezone`、各来源 `source_timezones`（GSC 常规日数据为 America/Los_Angeles、GA4 为 property 时区、CRM 为业务系统时区）、property、搜索类型、字段映射、URL 规范化和合格线索定义。每个 `source_metadata` 记录 `source_kind`、`data_as_of`、`finality`/`preliminary`、`row_limit_hit`、`pagination_complete`、适用时的 `sampling_rate`/`thresholding_applied`、`data_quality` 与 `attribution_model`。只有 `date` 粒度且来源日界不同或缺失时，工具禁止逐日跨源 join，只保留各来源显式窗口汇总；要恢复逐日对齐，需提供可转换到分析时区的 timestamp 粒度。工具直接拒绝 Query、邮箱、电话、lead/user ID 与原始 CRM 阶段行；缺值返回 null 和原因，不补 0。其最高自动判定仍是 directional，任何元数据缺失、冲突、触限、采样、阈值或 preliminary 都降级为 `inconclusive`，不能产出 `incremental-positive` 或 `no-detectable-change`。

配置中的测量完整性部分至少采用以下形状；其他窗口、字段映射与 URL/CRM 定义仍按项目填写：

```json
{
  "analysis_timezone": "Europe/Berlin",
  "source_timezones": {
    "gsc_page": "America/Los_Angeles",
    "ga4": "Europe/Berlin",
    "crm": "Europe/Berlin"
  },
  "source_metadata": {
    "gsc_page": {
      "source_kind": "gsc_search_analytics",
      "data_as_of": "2026-07-05T12:00:00Z",
      "finality": "final",
      "row_limit_hit": false,
      "pagination_complete": true,
      "data_quality": "complete"
    },
    "ga4": {
      "source_kind": "ga4_property_report",
      "data_as_of": "2026-07-05T12:00:00Z",
      "finality": "final",
      "row_limit_hit": false,
      "pagination_complete": true,
      "sampling_rate": 1,
      "thresholding_applied": false,
      "data_quality": "complete",
      "attribution_model": "data_driven"
    },
    "crm": {
      "source_kind": "crm_aggregate_export",
      "data_as_of": "2026-07-05T12:00:00Z",
      "finality": "final",
      "row_limit_hit": false,
      "pagination_complete": true,
      "data_quality": "complete",
      "attribution_model": "first_organic_landing_cohort"
    }
  }
}
```

```bash
python scripts/measurement_review.py \
  --gsc-page gsc-page.csv --ga4 ga4-landing.csv --crm crm-cohort.csv \
  --mapping measurement.json \
  --json-out .vibio/runs/business-review.json \
  --markdown-out .vibio/runs/business-review.md
```

如果实施前已用 `scripts/experiment.py plan` 冻结页面级随机 holdout 或匹配组 DiD，则在预注册观察窗口成熟后使用实验分析。panel CSV 必须包含实验单位、`date`、`group`、主指标、全部护栏，以及 `contaminated` 或 `treatment_applied`；每个实验单位必须覆盖基线与观察窗口的每一天，基线均值必须与冻结的逐页面摘要一致。缺日或换基线都直接进入 `inconclusive`。artifact report 的 `passed` 必须来自真实上线产物复验，并应携带同一 `experiment_id` 与 `plan_hash`。

```bash
python scripts/experiment.py analyze \
  --plan .vibio/experiments/seo-title-2026-01/frozen/plan.json \
  --panel .vibio/experiments/seo-title-2026-01/panel.csv \
  --artifact-report .vibio/experiments/seo-title-2026-01/artifact.json \
  --measurement-metadata .vibio/experiments/seo-title-2026-01/measurement-metadata.json \
  --out .vibio/experiments/seo-title-2026-01/result.json \
  --markdown-out
```

用 `schemas/experiment.report.schema.json` 校验结果。按以下边界解释：

- `implementation-failed` 表示 treatment 未通过产物验证，先修实现，不解释业务效果。
- `inconclusive` 表示窗口、数据、污染、护栏、区间或 MDE 精度门槛至少一项不合格，不能升级为增量结论。
- 实验 `measurement_contract` 必须在实施前冻结 `analysis_timezone`、`date` 粒度、source ID/kind/timezone、每个指标的唯一来源映射与适用的 attribution model。分析 metadata 只能补充 `data_as_of`、finality/preliminary、行数上限、分页、采样、阈值和 data quality 等采集状态，不得新增来源、修改冻结字段或事后补齐缺失的预注册合同。观察结束日当天仍未成熟；带时间的 `data_as_of` 要按来源时区越过次日零点，日期型值解释为完整 through date，未来截止点无效。缺失、冲突、采样或阈值处理直接进入 `inconclusive`。
- `eligible_incremental` 只表示结果具备人工增量解读资格。它不判断效果方向，也不自动证明 SEO、排名、流量或收入因果；只有预注册指标方向、置信区间、机制、对照假设和适用范围共同支持时，才可在已测试范围内判 `incremental-positive`。
- `experiment.py` 不在正式报告中自动声称功效。不得仅凭 `precision_sufficient_for_mde` 判 `no-detectable-change`；必须用 `state_manager.py detectability` 从同一冻结 plan 和正式 result 生成证据，只有确定性重算 power >= 0.8、置信区间包含 0 且其他完整性门禁全部通过才可写入该状态。

形成判定后，用 `scripts/state_manager.py append-review` 写入结构化状态，再用 `render` 生成 Markdown 视图。状态工具会阻止纯前后对比直接写成 `incremental-positive`。这两个强状态必须携带 `measurement_integrity: {status: complete, issues: [], evidence: ...}`，引用首条 planned 事件中预先注册的同一 plan、正式实验结果及其 SHA-256，并用 `experiment_inputs` 对 panel、artifact report 及可选 measurement metadata 逐文件提供 `{path, sha256}`。状态工具重放原始输入后，将结果与正式报告除 `analyzed_at` 外整份比较，额外字段也会被拒绝；`no-detectable-change` 还需绑定由状态工具生成的 detectability JSON 及 SHA-256。缺失、矛盾或证据文件变化时拒绝写入。

```bash
python scripts/state_manager.py detectability \
  --project-root . \
  --experiment-plan .vibio/experiments/seo-title-2026-01/frozen/plan.json \
  --experiment-result .vibio/experiments/seo-title-2026-01/result.json \
  --out .vibio/experiments/seo-title-2026-01/detectability.json
```

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

- GSC/GA4/CRM 可用：分别记录 analysis timezone 与 source timezones、property、过滤条件、日期、`data_as_of`、finality、分页/触限、采样/阈值、归因模型、覆盖率和匿名/隐藏数据限制。
- 只有导出：验证字段定义和同口径窗口后，用自带 GSC 工具保留来源 hash、维度粒度、property、搜索类型、时区和过滤条件；缺失契约时明确降级。
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

实验工具当前只实现页面级随机 holdout 和匹配页面 DiD。其他设计可以人工评估，但不能伪装成工具已验证；简单窗口对比继续按描述性证据处理。

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
