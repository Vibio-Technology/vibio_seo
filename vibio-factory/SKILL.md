---
name: vibio-factory
description: >-
  当用户要求“创建/改进 Vibio SEO Skill”“把 SEO 流程封装成 skill”“优化触发描述或 eval”“build an SEO skill”“improve vibio-*”时使用。本元 Skill 按 Vibio v5 的证据政策、薄编排架构、可选能力 fallback、根 references 单一真源和构建/校验流程创建或重构 Skill，并用正向与 near-miss eval 验证触发和输出。默认中文。不用于直接执行网站审计、修复、写作、规划或广告 Campaign。
compatibility: 需要 Vibio 仓库文件读写与 Python 校验环境。联网研究和外部 skill-creator 可选；若使用实时资料，必须保留来源与核验日期。
---

# Vibio FACTORY

默认用中文讨论、设计和交付 Skill；为了识别真实用户请求，可在 description 与 eval 中保留必要的英文 SEO 触发词。

FACTORY 生产的是可触发、可降级、可验证的薄编排器。方法论和易变事实放在根级 references；SKILL.md 只保留路由、决策流程、输入输出契约与硬边界。

## 必读资料

- `vibio.manifest.yaml`：Skill、角色、reference 策略和外部能力的仓库清单。
- `references/evidence-policy.md`：来源、数值和结论强度。
- `references/capability-routing.md`：能力/提供商选择与 fallback。
- `references/google-search-docs.md`：Google 当前规则与易变来源。
- `references/paid-search-intelligence.md`：广告能力在 SEO Skill 中的边界。
- `evals/schema/evals.schema.json`：发布 eval 的结构契约。

环境提供通用 `skill-creator` 时，先遵循其 intent、基线、测试和迭代流程；不可用时按本流程完成同等检查。不得因为辅助工具缺失而跳过仓库校验。

## 架构规则

1. `vibio/SKILL.md` 是总入口和模式路由器，不复制每个领域的完整方法论。
2. `vibio.manifest.yaml` 是 Skill 名称、路径、角色和外部能力的清单，不在正文硬编码“固定 N 个专家”。
3. 顶层 `references/` 是唯一人工维护真源。子 Skill 的 `references/` 是构建产物，不手工编辑。
4. `scripts/build_skills.py` 按 Markdown 引用闭包生成自包含副本；每个发布 Skill 必须能脱离 monorepo 解析自己的引用。
5. 外部 `seo-*`/`b2b-*` 能力必须在 manifest 声明为 optional，并提供在本地代码、渲染 HTML、官方来源或用户导出上可执行的 fallback。
6. `.vibio/` 是目标客户项目的状态，不是 Skill 仓库中的方法论真源。

## 创建或改进流程

### 1. 捕捉意图与边界

优先从对话、现有 Skill、失败案例和真实工作流提取：

```text
User decision / job to be done:
Positive trigger phrases (Chinese + needed English):
Near-miss requests that must not trigger:
Inputs and permissions:
Expected artifacts / report:
Required evidence:
Optional capabilities and fallback:
Success assertions:
```

只有答案会实质改变架构时才追问。改进现有 Skill 时保留 manifest 中的 name/path，先保存或使用既有基线用于对比。

### 2. 决定归属

- 现有模式中的一个步骤：优先改对应根 reference 或薄编排流程。
- 独立用户意图、输入输出和完成标准：才考虑新建子 Skill。
- 只是一个数据提供商：登记为可选 capability，不为它复制一个业务工作流。
- 与 SEO 无直接决策关系的广告运营、社媒运营或泛营销：拒绝塞进 Vibio SEO 模式。

### 3. 写 frontmatter

- `name` 与 manifest 完全一致，使用 kebab-case。
- `description` 同时写“何时触发、做什么、何时不触发”，覆盖中文真实说法和必要英文术语。
- 加入最有区分力的 near-miss 边界，避免兄弟 Skill 抢触发。
- `compatibility` 只写实际权限、工具和降级前提，不把可选 provider 写成必需依赖。
- 描述不得承诺排名、流量、固定 CTR/转化率/uplift 或工具不存在时的数据结果。

### 4. 写薄编排主体

主体通常包含：

1. 默认中文及目标市场语言规则。
2. 任务结果契约和证据优先级。
3. 启动时的项目记忆、真实产物和能力检查。
4. 分阶段决策/执行流程。
5. 外部能力可用与不可用两条路径。
6. 产物验证与效果复盘的分离。
7. 结构化输出、下一步路由和“不要做”。

把详细清单、模板、来源表和长方法论放入根 `references/`。真实引用写成 `references/<file>.md`，让构建器发现闭包；不要使用 `../references`。

### 5. 过 SEO 证据闸门

任何新/修改 Skill 都要排除以下无证据或过时行为：

- 把 `llms.txt`、特殊 AI Schema、内容切碎或合成提及当作 Google 排名/GEO 高杠杆项。
- 把 Google Indexing API 用于普通页面。
- 为 Google 富结果推荐已经停用的 FAQPage/HowTo 功能。
- 用固定 title/meta 字符数作为硬性合规规则。
- 承诺 Schema 提升排名或 AI 引用。
- 确定性连接 GSC query 与 GA4/CRM conversion。
- 填入无来源的 CTR、转化率、链接比例、流量或 uplift。

Google、Search Console、Ads、GA4、结构化数据和 AI Search 等易变论断在发布前核验实时官方来源，记录 canonical URL 与 `verified_on`。第三方资料只能支持有范围的观察或实验，不得冒充官方规则。

广告模块只能回答 SEO 的查询、意图、信息表达、落地页或合格转化决策；普通投放/报告只能形成额外需求和增量假设，只有合格对照才能估计增量。不得把广告支出写成自然排名因素，也不得扩展成泛投流工作流。

### 6. 设计 eval

每个发布 Skill 至少覆盖：

- 典型中文触发场景。
- 不点名 Skill、但任务意图明确的英文或混合语言场景。
- 与兄弟 Skill/广告运营相邻的 near-miss。
- 能力缺失时是否真实降级、是否拒绝虚构数据。
- 至少一个会暴露领域硬边界的场景。

按 `evals/schema/evals.schema.json` 编写 name、expected output 和 typed assertions。断言优先检查可观察行为：是否引用证据、是否说明未知、是否选择正确模式、是否产生规定产物；不要用主观“看起来专业”或固定字数替代质量。

改进现有 Skill 时，将新版本与 manifest 的基线/快照在同一批 prompts 上比较。路由评估包含 should-trigger 与 should-not-trigger，报告准确率和失败样本，不为追求单一分数过拟合措辞。

### 7. 构建与验证

先构建自包含引用，再执行严格校验和测试：

```bash
python scripts/build_skills.py --clean
python scripts/validate_repo.py --strict
pytest
git diff --check
```

若只开发一个 Skill，可用构建脚本的 `--skill <path>` 缩小反馈范围；发布前仍需全仓构建和严格校验。检查生成副本 hash、缺失引用、frontmatter、manifest 能力、eval schema、禁止路径和工作区意外改动。

### 8. 交付

报告：触发边界、架构变化、引用闭包、fallback、移除的风险规则、eval/校验结果、与基线的差异和残余风险。没有通过验证时不得宣称完成；测试受环境限制时明确列出未运行项。

## 不要做

- 不手改子 Skill 的生成 reference 副本或维护多份人工真源。
- 不把提供商输出、官方建议或第三方相关性硬编码成排名保证。
- 不为一个小步骤复制整个新 Skill。
- 不只测试正向触发，忽略 near-miss 和降级路径。
- 不用无证据的“SEO 分数”证明新版本更有效。
