# Vibio SEO Skills

> Vibio 的端到端 SEO 工具箱 — 一套把任意网站（任意技术栈，或只给一个 URL）变成可排名资产的 Claude Code skills

多 skill 架构：不在一个巨型 skill 里分模式，而是拆成**主入口路由 + 专项子 skill + 末尾下一步路由串成工作流**。

---

## Skills 列表

| Skill | 功能 | 触发方式 |
|-------|------|---------|
| `vibio` | 主入口，判断意图并路由 | `/vibio`、SEO 意图模糊时 |
| `vibio-plan` | PLAN 引擎：90 天路线图 + 周/月节奏 + 追踪 | 「排个 SEO 计划」「90 天路线图」 |
| `vibio-keyword` | KEYWORD 引擎：产品/业务 → 真实搜索量+意图 → 关键词族映射到页面 → 主题簇 | 「我的产品该做哪些词」「关键词研究」 |
| `vibio-audit` | AUDIT 引擎：读真实产物 → 对照 Google 官方文档 → 路由 27 个 seo-* 专家 → 优先级化发现 | 「审查我的站」「为什么排不上去」 |
| `vibio-fix` | FIX 引擎（栈无关）：识别栈 → 套通用目标规格 → 在 Next.js/WordPress/Shopify/静态站里落地，或给可粘贴片段 | 「加 schema」「修 OG 图」「让品牌名在 Google 显示」「给个网址帮我改好」 |
| `vibio-review` | REVIEW 引擎（闭环复盘）：读改动历史 → 等重抓窗口 → GSC+基线复测 → 判定见效 → 决定下一步 | 「上次改的见效了吗」「月度复盘」 |
| `vibio-factory` | 元技能：按本系列架构生产/优化新的 vibio 子 skill | 「把这个流程做成 skill」 |
| `vibio-memory` | 项目记忆层：读写项目根 `.vibio/`（诊断/进度/三张追踪表/改动日志） | 由 plan/audit/fix/review 调用；「继续上次的 SEO」 |

底层还路由 27 个独立的 `seo-*` 专家 skill（audit/technical/schema/content/geo/backlinks…），它们不属于本系列，由 `vibio-audit` 调度。审查以 Google 官方文档为基准（`vibio-audit/references/google-search-docs.md`，覆盖技术要求/结构化数据/垃圾政策/helpful content，每条带官方 URL，存疑时实时 WebFetch 核实）。

---

## 四种操作模式

每个请求先归类，由主入口 `vibio` 分发：

- **PLAN** → `vibio-plan`：「启动 SEO / 90 天路线图 / 每周做什么」。跑执行操作系统，按交付模板输出。
- **AUDIT** → `vibio-audit`：「审查我的站 / 检查页面 / 为什么排不上去」。读真实产物 → 对照 Google 官方文档 → 路由专家 → 优先级排序的发现 + 修复。
- **FIX** → `vibio-fix`：「优化页面 / 加 schema / 修 OG 图」或直接给个 URL。**栈无关**——所有 SEO 问题都暴露在渲染出的 HTML 里，跟谁生成的无关。先识别栈，用通用目标规格（`seo-fix-principles.md`）定义「要达成什么」，再按栈适配器（Next.js / WordPress / Shopify / 静态站 / URL-only）落地，最后在渲染产物里验证。
- **REVIEW** → `vibio-review`：「上次改的见效了吗 / 月度复盘」。读 `.vibio/` 改动历史 → 等够重抓窗口 → 用 GSC + 基线对比复测 → 判定见效 → 决定刷新/扩展/降级/推进。

专项入口 **`vibio-keyword`**（关键词研究）：「我的产品该做哪些词」。产品/业务 → 扩种子词 → `seo-dataforseo` 拉真实搜索量/难度/意图 → 按意图分类打分 → 关键词族映射到页面 → 主题簇 → 写 `.vibio/trackers/keywords.md`。是 PLAN 第 2 周"关键词架构"阶段的主力，也能独立触发。

一次会话常常串起来：**AUDIT → FIX → 把剩下的 PLAN 掉**；过段时间再 **REVIEW** 复测见效、回到下一个瓶颈，形成闭环。每个 skill 末尾的「下一步路由」表负责衔接，记忆层 `.vibio/` 把跨会话的历史串起来。

---

## 目录结构

```text
skills/
├── vibio/SKILL.md                       # 主入口路由器
├── vibio-plan/
│   ├── SKILL.md
│   ├── evals/evals.json
│   └── references/
│       ├── operating-system.md          # PLAN 引擎：kickoff/诊断/90天/节奏/追踪
│       └── delivery-template.md         # PLAN 交付标准结构
├── vibio-keyword/
│   ├── SKILL.md                       # KEYWORD 引擎：种子词→真实量/意图→词→页映射→簇
│   └── evals/evals.json
├── vibio-audit/
│   ├── SKILL.md
│   ├── evals/evals.json
│   └── references/
│       ├── skill-arsenal.md           # 27 个 seo-* 专家的能力地图与调度规则
│       ├── google-search-docs.md      # 审查基准：Google 官方文档蒸馏（每条带 URL）+ 混合用法
│       ├── seo-fix-principles.md      # 同步副本（权威源在 vibio-fix）：审查用的目标规格
│       └── stack-detection.md         # 同步副本（权威源在 vibio-fix）：识别栈传给 fix
├── vibio-fix/
│   ├── SKILL.md
│   ├── evals/evals.json
│   └── references/
│       ├── seo-fix-principles.md      # 栈无关目标规格 + 渲染产物验证（FIX 核心）
│       ├── stack-detection.md         # 从代码库/URL 指纹识别栈 + 判断能否改代码
│       └── stack-adapters/            # 各栈的落地方式
│           ├── nextjs.md              #   最完整，真实验证过的 App Router 配方
│           ├── wordpress.md           #   Yoast/Rank Math + 主题
│           ├── shopify.md             #   Liquid 模板 + 主题设置
│           ├── static-astro.md        #   Astro/Hugo/Jekyll/纯 HTML
│           └── url-only.md            #   无代码权限：给规格 + 可粘贴片段
├── vibio-review/
│   ├── SKILL.md                       # REVIEW 引擎：读改动历史→复测→判定见效→决策
│   └── evals/evals.json
├── vibio-memory/
│   ├── SKILL.md                       # 项目记忆：读写项目根 .vibio/
│   ├── evals/evals.json
│   └── references/
│       └── state-templates.md         # project.md / 三张 tracker / changelog 标准格式
└── vibio-factory/SKILL.md               # 造 skill 的元技能

> 项目记忆落在**被操作项目**的根目录 `.vibio/`（project.md + trackers/ + changelog.md），不在 skill 目录里。
```

---

## 设计原则（跨模式底线）

- 先看真实项目（代码库或 URL），再下计划
- 先找一个主瓶颈，再排优先级（不列五个并列优先级）
- 默认动手修，不只描述；栈无关——有代码改代码并 build/lint，托管平台给可粘贴片段，都在渲染产物里验证
- 能路由到 seo-* 专家就不手搓分析
- 以周/月为节奏，不做日常焦虑型 SEO
- 不承诺排名、不承诺快速见效
- 面向 SERP 的改动会提醒：需等搜索引擎重新抓取，可在 Search Console 请求索引加速
- 有记忆：每个项目落 `.vibio/`，开工先读、收工写回，从「每次重新认识项目」变成「记得上次干了什么」
- 审查有据：发现以 Google 官方文档为准并引到 URL，不靠民间 best practice

---

## 安装

把各 `vibio*` 目录复制到本地 skills 目录（如 `~/.claude/skills/`），重启客户端后用 `/vibio` 或自然语言触发。
