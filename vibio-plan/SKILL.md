---
name: vibio-plan
description: >-
  当用户要求“SEO 计划/策略”“90 天路线图”“内容日历”“先做什么页面”“weekly/monthly SEO plan”“SEO roadmap”时使用。本 Skill 从真实网站、业务目标、第一方数据与执行产能出发，识别当前资源焦点，同时暴露独立严重阻断，按依赖关系编排可交付、可验证、可停止的行动，并写入项目状态。默认中文；目标市场内容保留目标语言。seo-plan、b2b-seo、SERP、GSC 和广告数据能力均可选，缺失时按 manifest fallback。不用于首次深度审计、已知问题直接改代码、单篇正文写作或独立广告 Campaign 运营。
compatibility: 可从代码库、URL、内容清单、业务材料或数据导出规划。联网与外部 SEO/广告提供商非必需；数据不足时输出证据获取任务与明确假设。
---

# Vibio SEO PLAN

涉及性能、目录参数或 Bing 目标时，分别按需读取 `references/core-web-vitals.md`、`references/faceted-navigation.md` 与 `references/bing-webmaster-docs.md`，把字段证据、抓取空间和平台边界写进依赖与验证条件。

默认使用中文沟通和交付；目标市场 query、页面文案和数据维度保留原语言。项目允许写入状态时，使用 `scripts/state_manager.py` 初始化/验证结构化 `.vibio/state/`，并把计划先记录为 `planned`；不要在实施、产物复验和结果观察之前跳跃状态。实验变更应先生成冻结 plan，再把 `experiment_id`、项目内 plan 路径、plan 文件 SHA-256 与 `plan_hash` 放入该 change 的首条 `planned.experiment_registration`，然后才能实施。若原 change 已注册为普通计划，另建实验 change ID，不能事后改写历史。

默认用中文沟通和交付。目标市场的关键词、页面名称、metadata 与实验素材使用当地语言，不通过机械翻译代替需求验证。

PLAN 的结果是一组按依赖排序、能改变目标指标的执行承诺，不是最佳实践清单或排名保证。

## 必读资料

- `references/evidence-policy.md`：证据、数值与优先级规则。
- `references/capability-routing.md`：能力检查和 fallback。
- `references/operating-system.md`：生命周期、主瓶颈和任务 SOP 菜单。
- `references/delivery-template.md`：交付结构与延续模式。
- `references/roi-attribution.md`：业务结果与可用归因粒度。
- `references/seo-experimentation.md`：假设、对照、窗口和停止条件。
- `references/paid-search-intelligence.md`：把广告限定为 SEO 学习渠道。
- `references/state-templates.md`：项目状态和 tracker 格式。

`references/operating-system.md` 中的周期、产量和阈值示例只能作为编排提示；任何数值必须用该项目的资源、基线、方差、抓取情况和销售周期重新确定。`references/evidence-policy.md` 始终优先。

## 页面级实验计划工具

只有决策确实需要因果证据、改动可回滚、同类页面足以形成 treatment/control，且测量口径稳定时，才使用 `scripts/experiment.py`。它只支持 `randomized_page_holdout` 与 `matched_page_did`，明确拒绝纯前后对比。实验单位应是页面或匹配页面对，不得把用户、邮箱、线索 ID 或其他个人数据作为单位。

实施前创建实验 spec 与基线 CSV。spec 至少冻结以下字段，MDE、窗口和护栏必须来自该项目的业务意义、历史波动与可用样本，不能事后调整到“刚好显著”：

```json
{
  "experiment_id": "seo-title-2026-01",
  "design": "randomized_page_holdout",
  "unit_id_column": "page",
  "primary_metric": "organic_clicks",
  "primary_metric_direction": "increase",
  "guardrails": [
    {"metric": "qualified_lead_rate", "direction": "non_decrease", "threshold": 0.01}
  ],
  "seed": 20260711,
  "treatment_fraction": 0.5,
  "baseline_start": "2026-05-01",
  "baseline_end": "2026-05-31",
  "observation_start": "2026-06-01",
  "observation_end": "2026-06-30",
  "minimum_detectable_effect": {"value": 10, "scale": "absolute"},
  "alpha": 0.05,
  "paid_ads_role": "none",
  "measurement_contract": {
    "analysis_timezone": "Europe/Berlin",
    "temporal_grain": "date",
    "source_timezones": {"panel": "UTC"},
    "sources": {
      "panel": {
        "source_kind": "derived_experiment_panel",
        "source_timezone": "UTC",
        "metrics": ["organic_clicks", "qualified_lead_rate"],
        "attribution_model": "first_organic_landing_cohort",
        "data_as_of": "2026-05-31",
        "finality": "final",
        "row_limit_hit": false,
        "pagination_complete": true,
        "data_quality": "complete"
      }
    }
  }
}
```

基线 CSV 必须包含实验单位、主指标和全部护栏；匹配设计还需 `pair_id`。无 `date` 时，每个实验单位必须恰好一行窗口聚合；有 `date` 时，每个实验单位必须覆盖预注册基线窗口的每一天。计划会把逐页面基线摘要和摘要 hash 一并冻结，防止分析阶段换基线。冻结计划后不要重跑 seed 挑选更好分组，也不要覆盖原文件：

```bash
python scripts/experiment.py plan \
  --spec .vibio/experiments/seo-title-2026-01/spec.json \
  --baseline .vibio/experiments/seo-title-2026-01/baseline.csv \
  --out-dir .vibio/experiments/seo-title-2026-01/frozen
```

保存 `plan.json`、`assignments.csv` 与来源文件；`plan.json` 可按 `schemas/experiment.plan.schema.json` 验证。工具会锁定输入 hash、稳定分组、基线平衡与因果/广告边界。`measurement_contract` 要在实施前冻结 analysis timezone、粒度、source ID/kind/timezone、指标的唯一来源映射与 attribution model；分析 metadata 之后只能补充数据截止、finality、分页、触限、采样、阈值和 data quality 等采集状态，不能新增来源或改写冻结字段。工具不能保证样本量足够、实验最终为正或 SEO 结果增长。没有合理对照时，明确把方案降级为描述性监控，并在 REVIEW 中禁止因果措辞。

实验 panel 只接受完整 `date` 粒度。多来源原始 timestamp 应先按各自来源日界完成窗口汇总，再构造统一的逐页面日面板；不要把未实现的 timestamp panel 声明写进计划。观察结束日当天尚未成熟，至少要等来源时区越过次日零点，并拒绝晚于当前时刻的 `data_as_of`。

## 工作流

### 1. 判断新项目还是延续项目

1. 确认真实项目根。如存在 `.vibio/`，读取当前阶段、已完成项、主瓶颈、近期变更和待复盘实验，只规划下一段，不重新 kickoff。
2. 检查用户已经提供的代码、页面、sitemap、内容清单、GSC/分析/CRM/广告导出和团队材料。
3. 只询问会改变顺序的缺失信息；其余写成假设和验证任务。

### 2. 建立结果边界

确认：

```text
Business model and offer:
Primary qualified conversion:
Target country / language / buyer:
Site and domain state:
Rendering stack and edit access:
Available weekly capacity and owners:
Current measurement coverage:
Decision horizon:
```

对 B2B/服务业务区分原始线索、合格线索、销售接收/跟进、商机、成交和淘汰。没有业务数据时使用明确命名的 proxy，不把它称为收入或 ROI。

### 3. 做证据与能力地图

列出计划中的关键决策及所需证据。`seo-plan`、`b2b-seo`、`seo-google`、`seo-dataforseo`、`seo-firecrawl` 等外部能力仅在可用时调用；否则按 `references/capability-routing.md` 使用代码、导出、sitemap、有边界的人工 SERP/页面样本和用户资料。

缺失数据不能用通用搜索量、难度、CTR、转化率或 uplift 填空。将无法回答的事项转换为前置测量任务，而不是伪精确预测。

### 4. 识别资源焦点与并行严重阻断

从以下类别中选择当前资源焦点，并用项目证据说明为什么它最先限制有效自然搜索结果。独立的访问、索引、安全、人工处置或重大转化阻断不能因只有一个资源焦点而被延后：

- 搜索资格或技术阻断。
- 测量与转化定义缺失。
- 目标市场关键词/页面所有权不清。
- 页面类型与意图错配。
- 原创信息与内容系统不足。
- 内部发现和信息架构不足。
- 在技术、意图、内容均合格后的权威性缺口。

其他问题列为依赖或 later，不要同时宣布多个“第一优先级”。官方可选建议本身不能证明是主瓶颈。

### 5. 定义计划结果

以能在规划窗口内完成和验证的系统/页面结果表述目标，例如修复已确认索引阻断、完成目标市场页面映射、发布一组有一手证据的商业页面、建立合格线索测量或完成受控实验。不要承诺排名、流量或收入。

每项任务必须包含：

```text
Decision / purpose:
Evidence and confidence:
Owner and capacity:
Deliverable:
Dependency:
Artifact verification:
Outcome metric:
Observation window:
Stop / rollback condition:
```

### 6. 按依赖编排

根据主瓶颈安排用户要求或项目适合的决策窗口；30/60/90 天只能是用户指定或团队确有该规划节奏时的表达方式。常见依赖方向是：

1. 修复已验证的访问、索引或测量阻断。
2. 验证目标市场需求、搜索者身份、意图族和页面所有权。
3. 改善或创建具有原创证据、专家价值和明确转化路径的页面。
4. 通过相关内链改善发现与商业路径。
5. 页面资产就绪后开展正当的权威建设。
6. 在预设窗口复盘、保留有效动作并停止无效动作。

这是依赖图，不是每个项目必须照抄的日历。已完成的阶段跳过；重大迁移、人工处置或业务变化可改变顺序。

### 7. 付费搜索作为可选学习模块

只有某项 SEO 决策因自然数据慢或含糊而受阻，并且转化测量、市场控制、预算授权和停止规则齐备时，才加入小范围付费验证。写清：待验证的用语/意图/信息表达/落地页问题、主要合格结果、支出边界、样本限制和 SEO 回馈动作。

广告竞争程度不是自然关键词难度，广告支出不会提升自然排名。本计划不扩展为 Campaign、出价、素材轮换或日常投流管理。

### 8. 交付与落盘

按 `references/delivery-template.md` 输出，但至少包含：项目快照、主导约束及证据、假设/未知、依赖顺序、阶段任务、产能与负责人、验证/复盘设计、风险、停止条件和接下来三项动作。

用户要求本周或本月计划时压缩范围，不强行输出 90 天全文。项目允许维护状态时，按 `references/state-templates.md` 更新 `project.md`，只创建当前工作真正需要的 tracker，并保留来源与日期。

## 下一步路由

| 计划中的下一动作 | 模式 |
|---|---|
| 需要验证现状或未知根因 | AUDIT |
| 已知技术问题且有修改权限 | FIX |
| 验证目标市场需求和页面映射 | KEYWORD |
| 创建或升级目标页面 | WRITE |
| 改善内部发现或正当外部权威 | LINK |
| 观察窗口成熟 | REVIEW |

## 不要做

- 不输出与真实项目、目标市场和产能无关的通用 90 天模板。
- 不把固定 CTR、转化率、内容数量、链接数量或 uplift 当作目标。
- 不在可抓取性、意图和页面价值未解决时自动前置高级战术。
- 不把 GSC query 确定性连接到 GA4/CRM 转化。
- 不因外部能力缺失而虚构搜索量、难度、SERP 或业务数据。
