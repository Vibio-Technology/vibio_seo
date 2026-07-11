---
name: vibio-memory
description: >-
  当用户说“继续上次的 SEO”“之前做到哪了”“记录这次发现/改动/复盘”“show SEO project history”，或其他 Vibio 模式需要读取、更新项目状态时使用。本 Skill 规定 `.vibio/` 的证据化记忆协议：保留项目事实、决策、变更、来源、验证、观察窗口和未知项，避免下一次从零开始。默认中文；不需要任何外部 seo-* 能力。不用于泛 SEO 问答、未经授权的跨项目数据汇总或把假设写成事实。
compatibility: 需要目标项目根目录的文件读取权限；写回需要项目内写权限。不得把凭据、个人数据或客户可识别敏感信息写入记忆。
---

# Vibio SEO MEMORY

默认用中文维护状态；目标市场 query、页面标题、URL、事件名和来源原文保持原语言。

MEMORY 是项目决策记录，不是搜索效果数据库。它只保存足以让下一次行动延续的事实、证据、假设和待验证事项，不制造原数据中不存在的精度。

## 必读资料

- `references/state-templates.md`：`.vibio/` 文件结构与字段模板。
- `references/evidence-policy.md`：证据等级、来源、数值与不确定性。
- `references/roi-attribution.md`：GSC、分析平台和 CRM 的粒度边界。
- `references/learning-loop.md`：仅在用户明确启用跨项目匿名经验库时读取。

模板负责结构，不负责证明领域结论；模板中的任何示例数字、标签或解释都必须服从当前证据政策和真实项目数据。

## 存储边界

默认状态位于被操作项目的根目录：

```text
.vibio/
├── project.md
├── changelog.md
└── trackers/
    ├── content.md
    ├── keywords.md
    ├── outreach.md
    └── links.md
```

只创建当前工作需要的文件；不要为了“完整”生成空 tracker。URL-only 任务先明确本地工作目录和目标 URL，再创建状态，不得写入 Skill 安装目录。

## 读取协议

1. 识别真实项目根，不能仅凭当前 shell 目录猜测。
2. 先读 `project.md`，再按任务读取相关 tracker 和 `changelog.md` 最近条目。
3. 提取当前阶段、主导约束、已验证事实、已实施变更、未完成依赖、待复盘窗口和已知数据缺口。
4. 检查记录的来源、日期、市场、页面范围和指标定义是否仍适用。
5. 用一句话向用户确认恢复点，然后只继续下一段工作，不重启整个流程。

文件不存在不是错误：说明没有持久基线，从当前真实产物建立最小状态即可。记忆与当前渲染产物或第一方数据冲突时，以更新、更强的证据为准，并通过新日志纠正，不能静默改写历史。

## 写入协议

只写会改变后续决策的信息：

- `project.md`：业务/市场/技术栈、主要合格转化、主导约束、当前阶段、目标和下一动作。
- `changelog.md`：已观察发现、实际实施变更、产物验证、复盘结论和状态转移；保持 append-only、新条目在顶部。
- `trackers/content.md`：真实页面/内容资产的所有权、状态和来源。
- `trackers/keywords.md`：经目标市场证据验证的 query/意图族及所属页面；无数据时不填搜索量、难度或排名。
- `trackers/links.md`：从抓取/导出验证的内部链接问题和回填动作。
- `trackers/outreach.md`：经人工确认的目标、接触状态和结果；不虚构权威指标或链接价值。

每条高影响记录至少保留：

```text
Observed fact or decision:
Evidence level:
Source / dataset and verified_on:
Market / page scope:
Confidence:
Action or change:
Artifact verification:
Outcome metric and observation window:
Owner / dependency:
Unknowns / stop or rollback condition:
```

状态值要区分：`observed`、`estimated`、`hypothesis`、`implemented`、`artifact-verified`、`outcome-pending`、`not-yet-observable`、`directional-positive`、`incremental-positive`、`no-detectable-change`、`negative-or-regression`、`inconclusive`。构建成功只能进入 `artifact-verified`，不能自动进入“已收录/已排名/已见效”。

## 数据完整性

- 记录日期范围、时区、property/view、过滤条件和数据覆盖限制。
- GSC query 可用于搜索表现分析，但不能确定性连接到 GA4 用户、CRM 线索或收入。
- 业务结果默认落在 landing page、市场、设备、日期 cohort 或意图簇等共享聚合维度。
- 预测、行业观察和计划假设要与实测值分列，不能回写成已实现结果。
- 不存 API key、cookie、访问令牌、未脱敏联系人、报价、合同、CRM 原始个人记录或其他秘密。

## 各模式写回

| 模式 | 最小写回 |
|---|---|
| PLAN | 主导约束、目标、依赖路线、负责人和下一动作 |
| AUDIT | 已验证发现、范围、来源、优先级与待修项 |
| FIX | 变更位置、产物验证、待观察指标和回滚条件 |
| KEYWORD/WRITE/LINK | 已验证映射或资产状态及来源 |
| REVIEW | 比较窗口、证据强度、判定与下一决策 |

如果只是概念问答或没有形成持久决策，不强制写回。

## 跨项目经验

`.vibio/` 是默认且唯一自动使用的状态层。只有用户明确同意跨项目积累经验时，才按 `references/learning-loop.md` 使用项目外经验库；写入前必须匿名化并删除域名、公司名、联系人、原始查询/收入明细等可识别信息。单例或相关性观察不能升级为通用规则，方法论修订仍需人工确认。

## 不要做

- 不覆写或删除 changelog 历史来“整理”结论。
- 不把缺失数据补成零，也不把未知排名、CTR、转化率或收入写成实测值。
- 不让旧记忆覆盖新的官方规则、真实渲染产物或第一方数据。
- 不在未确认项目根与写入授权时创建 `.vibio/`。
- 不自动把客户项目数据写入全局或其他项目。
