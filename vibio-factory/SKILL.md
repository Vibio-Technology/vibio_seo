---
name: vibio-factory
description: |
  当用户想「创建一个 vibio 子 skill」「把这个 SEO 流程做成 skill」「改进 / 优化某个 vibio skill」「这个重复流程能不能封装成工具」时，应使用本 skill。
  这是生产和优化 Vibio SEO skill 的元技能：按本系列约定的架构（主入口路由 + 专项子 skill + references 渐进披露 + 末尾下一步路由）生成或重构 skill，并校准 description 的触发词。
  不应触发：直接做 SEO 规划/审查/修复本身（用 vibio-plan / vibio-audit / vibio-fix）、与封装 skill 无关的任务。
  Use when the user wants to create, build, improve, or optimize a vibio-* SEO skill, or turn a repeatable SEO workflow into a reusable skill following the Vibio architecture.
---

# Vibio-Factory — SEO Skill 生产工厂

用于按 Vibio 系列架构创建和优化 SEO skill 的元技能。如果已装有通用的 `skill-creator`，它负责通用 skill；本工厂专管 vibio-* 系列的一致性。

---

## Vibio 系列架构（必须遵守）

```
vibio/              主入口路由器：判断 PLAN/AUDIT/FIX 意图 → 分发到专项子 skill
vibio-plan/         PLAN 引擎（references: operating-system.md + delivery-template.md）
vibio-keyword/       KEYWORD 引擎（关键词研究：种子词→真实量/意图→词→页映射→簇；PLAN 前置/可独立触发）
vibio-audit/        AUDIT 引擎（references: skill-arsenal.md 路由 27 个专家 + google-search-docs.md 官方审查基准）
vibio-fix/          FIX 引擎（栈无关：seo-fix-principles.md + stack-detection.md + stack-adapters/）
vibio-review/       REVIEW 引擎（闭环复盘：读 changelog→复测 GSC/drift→判定见效→决策→写回）
vibio-memory/       项目记忆的格式规范与读写约定（.vibio/）；各 skill 自己用 Read/Write 操作，非互相调用
vibio-<新模式>/      新增的专项 skill，自包含自己的 references
```

每个子 skill 是自包含目录：
```
vibio-xxx/
├── SKILL.md          必需：YAML frontmatter + Markdown 指令
└── references/       可选：按需加载的重资料（>300 行时提供目录）
    └── *.md
```

**三级渐进披露：**

| 层级 | 内容 | 加载时机 |
|------|------|---------|
| Metadata | name + description | 始终在上下文（~100 词）|
| SKILL.md 主体 | 核心流程和指令 | skill 触发时（理想 <200 行）|
| references | 详细规范/模板/数据 | 用到时才 Read |

---

## 创建流程

### 第一步：捕捉意图
先从对话历史提取——如果用户说「把这个流程做成 skill」，不要从零问，直接提取：用了哪些工具、步骤顺序、用户做过哪些纠正、输入输出格式。让用户确认后再继续。全新需求才收集：这个 skill 做什么 / 用什么词触发（精确短语，含中英文）/ 输出什么格式。

### 第二步：决定归属
- 是 PLAN/AUDIT/FIX 之一的子能力？→ 考虑并入现有子 skill 的 reference，而非新建。
- 是一种全新的操作模式？→ 新建 `vibio-<模式>` 目录，并在 `vibio/SKILL.md` 的工具地图 + 路由规则里登记。

### 第三步：写 description（触发机制的核心）
用第三人称，三段式：
1. **正向触发**：列出用户会说的精确短语，中英文都给。「即使用户没说 X，只要他们想 Y，也应触发」。
2. **做什么**：一句话说清流程和输出。
3. **反向排除**：`不应触发：...（用 vibio-yyy）`，明确划清与兄弟 skill 的边界。

```yaml
# ✅ 正确：有精确触发短语 + 反向排除
description: |
  当用户说「加 schema」「修 OG 图」时应使用本 skill。用验证过的配方直接改代码并 build/lint 验证。
  不应触发：要执行计划（用 vibio-plan）、要先诊断（用 vibio-audit）。

# ❌ 错误：模糊，无触发短语，无边界
description: Provides SEO fix guidance.
```

两类触发问题：**触发不足** → 补更多短语和意图描述；**误触发** → 加 `不应触发 / DO NOT trigger when...`。

### 第四步：写 SKILL.md 主体
- 开头一句话立人设（「你不是 X，你是 Y」），定核心约束。
- 用 Step / Phase 写可执行流程，不是理论。
- 重资料（模板、长清单、数据驱动配方）拆到 references，正文用一句「需要 X 时 Read references/xxx.md」引用。
- **末尾必须有「下一步路由」表**：跑完推荐串到哪个兄弟 skill（这是本系列把多个 skill 编排成工作流的关键）。
- 结尾给「不要做」清单，划出反模式。

### 第五步：登记与验证
- 新建子 skill 必须在 `vibio/SKILL.md` 的工具地图和路由规则里加一行。
- 写 evals：至少 3 条 `{prompt, expected_output}`，覆盖典型触发场景，放本 skill 的 `evals/evals.json`。
- 自检触发词与兄弟 skill 是否冲突（同一句话不应同时强匹配两个 skill）。

---

## 本系列的约定（不要破坏）

1. **主入口只路由，不干活**：`vibio` 不实现分析，只判断意图分发。
2. **专家不重造**：底层 27 个 `seo-*` 由 `vibio-audit` 路由，新 skill 不重复实现它们的分析。
3. **末尾路由串工作流**：AUDIT → FIX → PLAN 靠各 skill 末尾的路由表衔接。
4. **跨模式底线一致**：先看真实项目、从主瓶颈出发、默认动手修、不承诺排名、以周/月为节奏。
5. **改完必验证**：涉及代码的 skill 必须含 build/lint 或渲染产物验证仪式。
6. **先读记忆、收工写回**：处理具体项目的 skill 要在开工前用 `Read` 读 `.vibio/`、收工后用 `Write`/`Edit` 写回（按 `vibio-memory` 的格式约定），不重启已诊断的项目。skill 之间不互相调用，记忆靠各自直接读写文件。
7. **审查引官方**：做审查判断的 skill 要以 `vibio-audit/references/google-search-docs.md` 为基准，结论引到官方 URL，存疑时 WebFetch 核实。

---

## 不要做

- 不为一个本属于现有子 skill 的小能力新建整个 skill 目录。
- 不写没有反向排除的 description（会和兄弟 skill 抢触发）。
- 不在主体里堆理论；能放 reference 的就放 reference。
- 新建 skill 后不登记到 `vibio/SKILL.md`，导致主入口路由不到。
