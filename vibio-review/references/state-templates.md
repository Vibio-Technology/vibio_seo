# 状态模板

结构化状态优先使用 `scripts/state_manager.py` 维护：

```text
.vibio/state/
├── project.json
├── project.sha256
├── changes.jsonl
└── reviews.jsonl
```

`project.sha256` 锁定项目身份；`changes.jsonl` 与 `reviews.jsonl` 是绑定项目摘要和另一条链 head 的追加式 SHA-256 链，跨进程写入由文件锁串行化。状态转移、复盘资格和敏感信息由工具校验；不要手改或覆写。下面的 Markdown 模板用于兼容旧项目或由 `state_manager.py render` 生成的人读视图，不再声称可通过自由文本可靠机械解析。迁移旧项目时先保留原文件，再从可验证记录初始化结构化状态，不能把历史推测成事实。该机制提供项目内篡改证据，不是外部签名；需要更强不可抵赖性时，把链 head 另存到受控的外部日志或版本库。

需要实验强结论时，先由 `experiment.py plan` 生成冻结计划，再在实施前把下面对象放入该 change 的首条 `planned` 记录。文件摘要必须来自实际 plan 文件；复盘时状态工具会重新读取并绑定正式 result、数值方向、CI、guardrail 与证据摘要。首条 planned 未注册的实验不能事后冒充预注册：

```json
{
  "experiment_registration": {
    "experiment_id": "seo-exp-001",
    "plan": ".vibio/experiments/seo-exp-001/frozen/plan.json",
    "plan_file_sha256": "<64 hex>",
    "plan_hash": "<plan.json 中的 plan_hash>"
  }
}
```

强结论的 review 记录还必须绑定产生 result 的原始输入。`measurement_metadata` 只在分析时确实提供该文件时出现；所有路径必须位于项目内：

```json
{
  "experiment_plan": ".vibio/experiments/seo-exp-001/frozen/plan.json",
  "experiment_result": ".vibio/experiments/seo-exp-001/result.json",
  "experiment_result_sha256": "<64 hex>",
  "experiment_inputs": {
    "panel": {
      "path": ".vibio/experiments/seo-exp-001/panel.csv",
      "sha256": "<64 hex>"
    },
    "artifact_report": {
      "path": ".vibio/experiments/seo-exp-001/artifact.json",
      "sha256": "<64 hex>"
    },
    "measurement_metadata": {
      "path": ".vibio/experiments/seo-exp-001/measurement-metadata.json",
      "sha256": "<64 hex>"
    }
  }
}
```

状态工具会重跑 `experiment.py analyze` 并比对除 `analyzed_at` 外的整份正式报告，额外字段同样会被拒绝。因此，加入自定义因果声明、修改报告数值后重算 result SHA-256，或使用另一份 panel 生成内部自洽报告，都不能通过强结论门禁。

`no-detectable-change` 不能使用手写 `power=0.8` 作为独立功效证据。先让状态工具从冻结计划与正式实验报告确定性生成证据：

```bash
python scripts/state_manager.py detectability \
  --project-root . \
  --experiment-plan .vibio/experiments/seo-exp-001/frozen/plan.json \
  --experiment-result .vibio/experiments/seo-exp-001/result.json \
  --out .vibio/experiments/seo-exp-001/detectability.json
```

证据会固定 `vibio-seo-detectability` 的 tool/version/method、plan/panel/artifact/measurement metadata/result 摘要、alpha、结构化 MDE、标准误与置信区间，并用双侧正态近似重算 power。review 记录必须保存该文件路径与 SHA-256；状态工具会再次重算整份证据，只有 power >= 0.8 且正式实验置信区间包含 0 时才允许 `no-detectable-change`。

0.8 是 v5 强状态的项目内验收门槛，不是通用样本量、无效果证明或排名保证。双侧正态近似不能修复错误设计、页面非独立、污染、数据不完整或机制不成立。

日期使用 `YYYY-MM-DD`。只填写已知事实，其余留空或标 unknown，不得编造。

`.vibio/` 是唯一自动使用的状态层。只有用户明确授权时，才能使用项目外经验库，并遵守 `learning-loop.md` 的匿名化、证据与人工审查协议；默认不得创建或读取全局层。只有用户授权项目内写入时，才能运行 init/append；读取与 validate 不扩大写权限。

---

## project.md

```md
# <项目名称> - SEO 状态

> 项目状态唯一真源。由 PLAN 更新诊断/路线，由 AUDIT 更新状态/技术栈；每次先读本文件。

## 快照
- 站点 / URL：
- 技术栈：（Next.js / WordPress / Shopify / static / unknown）
- 编辑模式：（code / template / CMS-paste）
- 商业模式：
- 主要合格转化：
- 目标市场 / 语言：
- 搜索基线 / 已知历史：
- GSC 已验证：（yes/no）  GA4：（yes/no）

## 诊断（来自 PLAN）
- 主要类别：
- 次级标签：
- 当前资源焦点：
- 独立严重阻断：
- 决策窗口 / 原因：
- 可验证结果：
- 最近复盘：YYYY-MM-DD

## 决策队列
| 层级 | 决策 / 交付物 | 依赖 | 进入证据 | 完成判据 | 负责人 | 状态 |
|---|---|---|---|---|---|---|
| now | | | | | | |
| next | | | | | | |
| later | | | | | | |

层级表示资源顺序，不是固定周/月。只有依赖或证据条件改变时才移动事项，并记录决策日期与原因。

## 当前阶段与下一约束
- 当前在做：
- 已完成：
- 下一行动：

## 未决问题 / 风险
- ...
```

---

## trackers/content.md

```md
# 内容跟踪表

| 标题 | URL | 页型 | 查询族 | 意图 | 状态 | 发布日 | 更新日 | 负责人 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | planned | | | | |

状态值：planned / drafting / published / refresh-needed / merged / redirected / retired
```

---

## trackers/keywords.md

```md
# 关键词跟踪表

| 查询族 | 市场 / 语言 | 买家 / 任务 | 意图 | 验证 | 拒绝原因 / 日期 | 主页面 | 投资层级 | 需求来源 | 难度证据 | 当前信号 | 上次信号 | 趋势 | 备注 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | not-yet-observed | |

验证值：pass / conditional / reject（按 `keyword-validation.md` 五道关卡）。保留被拒词及原因、来源和决策日期，避免后续重复研究或悄悄恢复已否定映射。
投资值：now / next / later / reject（按 `authority-cascade.md`，依据业务价值、需求证据、意图、信息增益、依赖与可测性，不用固定 KD 分层）。
难度证据：记录提供商或 SERP 证据、市场和核验日期；无法得知时写 unknown，不编分数。
趋势值：improving / flat / declining / not-yet-observed / insufficient-data。
数据达到可比窗口成熟度后再复盘，并保留带日期历史。
```

---

## trackers/outreach.md

```md
# 外联跟踪表（权威建设开始后创建；流程见 backlink-playbook.md）

| 目标站点 | 联系人 / 渠道 | 类型 | 推广页面 | 发送日期 | 跟进 | 状态 | 结果 |
|---|---|---|---|---|---|---|---|
| | | | | | | not-started | |

类型值：directory / association / certification / trade-show / partner / guest-post / product-review / media-request / digital-PR / expert-quote / reclaim / broken-link / resource。
状态值：not-started / drafted / pending-human-review / sent / follow-up-due / in-conversation / won / lost。
Agent 最多推进到 pending-human-review；由人类发送/注册后回填 sent 及后续状态，详见 `backlink-playbook.md` 的执行边界。
结果填写链接 URL 或 `mention-unlinked`。将提及作为 PR、品牌需求或引荐证据追踪，不假设它会造成 AI 引用或排名提升。
```

---

## trackers/links.md（可选，首次内链审计时创建）

```md
# 内链健康（按 link-architecture.md；在项目适合的时机刷新）

最近审计：YYYY-MM-DD

## 孤立页面（inlinks = 0）
- URL - 计划 donor 页面

## 发现路径弱或相关支持不足的优先页面
- URL - 已观察问题 / 可比证据 - 计划 donors

## 回填队列（等待入链的新页面）
- URL - 发布日期 - donor 页面 + 锚文本 - 是否完成 / 决策日期（发布、迁移或队列影响发现时复查；保留完成历史）

## 商业页面入链记录
| 页面 | 入链数 | 点击深度 | 最近 donor 检查 |
|---|---|---|---|
```

---

## changelog.md

```md
# 变更日志

> 保留历史。每条 AUDIT 发现和 FIX 变更都新增带日期记录，不覆盖或删除旧条目；使用一致顺序并在此注明顺序约定。

## YYYY-MM-DD - <AUDIT|FIX|REVIEW> - <短标题>
- 类型：AUDIT finding | FIX change | REVIEW conclusion
- 严重度（审计）：Critical / High / Medium / Low
- 内容：<发现、变更或结论>
- 位置：<文件 / 模板 / CMS 位置 / URL>
- 验证：<build/lint、渲染 HTML 检查，或 pending re-crawl>
- 状态：open / fixed / deferred
- 参考：<引用 Google 政策时填官方 URL>

## YYYY-MM-DD — ...
```

---

## 可选：technical-log

只有技术工作量确实需要第四张 tracker 时才创建（见 `operating-system.md`）；否则技术问题作为 `Type: AUDIT finding` 条目写入 `changelog.md`。
