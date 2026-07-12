# Vibio SEO v5 中文使用教程

这份教程面向第一次安装和使用 Vibio SEO v5 的用户，也包含手动运行确定性工具、效果复盘和实验的进阶说明。建议先完成“5 分钟离线验收”和“第一次真实项目审计”，再阅读后面的高级章节。

Vibio 能帮助你把 SEO 工作变成一套有证据、能实施、可验证、可复盘的流程。它不能保证具体排名、流量、AI 展示、收入或固定见效时间。代码构建成功只证明产物存在；抓取、索引、搜索表现和业务结果必须在数据成熟后分别验证。

按你的目标选择阅读路线：

- 想立刻用起来：阅读第 1-5 节。
- 不知道该调用哪个能力：阅读第 7-9 节。
- 要手动运行脚本或接入 CI：阅读第 10 节。
- 要判断 SEO 是否真的有效：阅读第 11 节。
- 遇到报错：直接查看第 13 节。

## 目录

1. [先理解四个概念](#1-先理解四个概念)
2. [准备环境和项目资料](#2-准备环境和项目资料)
3. [安装 Vibio](#3-安装-vibio)
4. [5 分钟离线验收](#4-5-分钟离线验收)
5. [第一次真实项目审计](#5-第一次真实项目审计)
6. [明确授权边界](#6-明确授权边界)
7. [选择八种工作模式](#7-选择八种工作模式)
8. [选择正确的证据输入](#8-选择正确的证据输入)
9. [四条常用工作流](#9-四条常用工作流)
10. [手动运行六个确定性工具](#10-手动运行六个确定性工具)
11. [理解报告与效果结论](#11-理解报告与效果结论)
12. [数据、隐私和安全边界](#12-数据隐私和安全边界)
13. [常见问题排查](#13-常见问题排查)
14. [升级、卸载和开发者验证](#14-升级卸载和开发者验证)
15. [最终检查清单](#15-最终检查清单)

## 1. 先理解四个概念

### 1.1 Skill、模式、脚本和状态

| 概念 | 作用 | 你如何使用 |
|---|---|---|
| Skill | 给 Codex 或其他兼容客户端提供 SEO 工作方法、证据规则和执行边界 | 在对话中说“请使用 `vibio-seo`” |
| 工作模式 | 表示当前阶段：规划、审计、修复、写作、关键词、链接、复盘或恢复 | 默认让 `vibio-seo` 自动路由；明确阶段时可直接调用专项 Skill |
| 确定性脚本 | 对 HTML、GSC、聚合业务数据、实验和项目状态执行可复验计算 | Agent 可自动运行；你也可以在终端手动运行 |
| `.vibio/` | 保存目标项目的身份、变更和复盘历史 | 只放在被优化的网站项目根目录，并且只有明确授权后才写入 |

Vibio 一共注册 10 个 Skill 目录，但业务上是八种 SEO 工作模式：

- `vibio-seo` 是总路由器。
- PLAN、AUDIT、FIX、WRITE、KEYWORD、LINK、REVIEW 有独立专项 Skill。
- RECOVER 由 `vibio-seo` 直接执行，没有单独的 `vibio-recover` 目录。
- `vibio-memory` 是项目状态支持层，不是第九种业务模式。
- `vibio-factory` 用于维护或扩展 Skill，不用于直接执行 SEO。

### 1.2 三个目录不要混淆

| 名称 | 示例 | 存放内容 |
|---|---|---|
| `VIBIO_REPO` | `~/src/vibio_seo` | Vibio 源码、构建器、测试和示例数据 |
| `SKILLS_ROOT` | `~/.codex/skills` | 构建完成后安装给 Codex 的 Skill 目录 |
| `TARGET_PROJECT` | `~/src/company-site` | 真正要优化的网站代码、数据、报告和 `.vibio/` |

最常见的错误是在 `VIBIO_REPO` 或 `SKILLS_ROOT` 中初始化真实项目状态。真实 `.vibio/` 必须属于 `TARGET_PROJECT`。

## 2. 准备环境和项目资料

### 2.1 环境要求

- Python 3.10 或更高版本。
- 一个支持 `SKILL.md` 的 Agent 客户端；下面以 Codex 为例。
- 如需修改网站，Agent 必须能访问目标代码库或 CMS 导出。
- 联网、GSC、GA4、CRM、SERP、抓取和广告数据都是可选能力；缺少时仍可执行降级版，但结论强度会降低。
- Windows 使用 IANA 时区时需要安装 `tzdata`；项目依赖已声明这一条件。

检查 Python：

```bash
python --version
```

输出应为 `Python 3.10` 或更高版本。

### 2.2 第一次开工至少准备什么

没有完整数据也可以开始，但至少要明确以下五项：

1. 站点 URL 或目标代码库路径。
2. 目标国家/地区和目标语言，例如 `DE`、`de-DE`。
3. 主要合格转化，例如有效询盘、试用、下单或预约。
4. 当前问题或目标，例如“产品页未获得自然曝光”。
5. 允许 Agent 做什么：只读、写报告、写 `.vibio/`、改代码、联网、部署或操作外部系统。

推荐补充：

- sitemap、robots.txt、静态构建目录或代表性浏览器 DOM。
- GSC、GA4、CRM 的聚合导出及数据截止时间。
- 近期 SEO 变更、发布日期和部署记录。
- 目标客户/RFQ 用语、产品事实、专家材料和合规限制。
- 可用的人力、审批、CMS 和开发约束。

不要为了“补齐资料”而提供 API key、Cookie、密码、联系人名单或 CRM 原始个人记录。

## 3. 安装 Vibio

### 3.1 在源码仓库构建和校验

进入 `VIBIO_REPO`，确认你使用的是 v5 分支：

```bash
cd /path/to/vibio_seo
git branch --show-current
```

创建开发环境：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Windows PowerShell 激活命令：

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
```

除标注为 PowerShell 的代码块外，本教程的 shell 示例使用 macOS、Linux、WSL 或 Git Bash 语法。Windows 原生 PowerShell 可以执行相同的 `python ...` 命令，但环境变量、文件复制和续行语法不同；不熟悉转换时优先使用 WSL 或 Git Bash。

构建自包含 Skill 并运行严格校验：

```bash
python scripts/build_skills.py --clean
python scripts/validate_repo.py --strict
```

成功标准是严格校验显示 `0 errors, 0 warnings`。如果失败，不要安装半构建版本。

### 3.2 安装到 Codex

普通 SEO 用户推荐安装路由器、七个专项模式和状态支持层：

```bash
skills_root="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills_root"
cp -R vibio vibio-plan vibio-audit vibio-fix vibio-keyword \
  vibio-content vibio-link vibio-review vibio-memory \
  "$skills_root/"
```

只有要创建或维护 Vibio Skill 时再安装 `vibio-factory`：

```bash
cp -R vibio-factory "$skills_root/"
```

最小安装只复制 `vibio/` 也能使用总路由器及全部六个运行脚本；安装专项 Skill 的好处是直接触发更准确。

更新旧安装时，先备份或移走旧的 `vibio*` 目录，再复制新版本，避免旧生成文件残留。不要只复制顶层 `references/`，因为每个安装目录已经带有构建后的引用、脚本和 Schema 闭包。

### 3.3 验证安装

```bash
test -f "$skills_root/vibio/SKILL.md"
test -f "$skills_root/vibio-audit/scripts/seo_inspect.py"
python "$skills_root/vibio-audit/scripts/seo_inspect.py" --help
```

安装后新开或重启 Codex 会话，让客户端重新读取 Skill 目录。第一次对话建议显式写出 Skill 名称：

```text
请使用 vibio-seo。先告诉我你识别到的目标项目根目录和准备采用的工作模式，不要修改任何文件。
```

如果客户端支持 `$skill-name` 语法，也可以写 `$vibio-seo`。

## 4. 5 分钟离线验收

这一节使用仓库自带 fixture，不访问真实网站，也不证明任何 SEO 效果。它只验证脚本、依赖和报告生成是否正常。

在 `VIBIO_REPO` 中创建临时输出目录：

```bash
demo_out="${TMPDIR:-/tmp}/vibio-seo-demo"
mkdir -p "$demo_out"
```

### 4.1 运行静态站审计

```bash
python vibio-audit/scripts/seo_inspect.py \
  --site-dir vibio-audit/evals/fixtures/industrial-site \
  --base-url https://example-industrial.test/ \
  --sitemap vibio-audit/evals/fixtures/industrial-site/sitemap.xml \
  --robots vibio-audit/evals/fixtures/industrial-site/robots.txt \
  --production \
  --json-out "$demo_out/audit.json" \
  --markdown-out "$demo_out/audit.md"
```

预期：

- 退出码为 `0`。
- 生成 `audit.json` 和中文 `audit.md`。
- 解析 3 个页面。
- 报告至少包含以下问题代码：

```text
robots.noindex
signals.noindex-cross-canonical
sitemap.noindex-url
sitemap.noncanonical-url
links.broken-internal
links.parameter-url-observed
structured-data.invalid-json
hreflang.return-link-missing
robots.unsupported-noindex
```

查看人读报告：

```bash
sed -n '1,220p' "$demo_out/audit.md"
```

### 4.2 运行 GSC 窗口比较

```bash
python vibio-review/scripts/gsc_compare.py \
  --input vibio-review/evals/fixtures/gsc-page-daily.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example-industrial.test \
  --search-type web \
  --analysis-timezone Europe/Berlin \
  --source-timezone America/Los_Angeles \
  --data-as-of 2026-07-05T12:00:00Z \
  --finality final \
  --no-row-limit-hit \
  --pagination-complete \
  --data-quality complete \
  --filter-notes "country=DE" \
  --json-out "$demo_out/gsc.json" \
  --markdown-out "$demo_out/gsc.md"
```

预期核心值：

| 指标 | 基线 | 当前 | 变化 |
|---|---:|---:|---:|
| Clicks | 14 | 19 | +5 |
| Impressions | 150 | 220 | +70 |
| CTR | 9.3333% | 8.6364% | -0.697 个百分点 |
| 加权 Position | 6.0000 | 4.8182 | -1.1818 |

工具会从 Clicks 和 Impressions 重算 CTR，不信任导出文件中可能错误的 CTR 汇总列。这个报告只能描述变化，不能证明变化由某项 SEO 修改造成。

### 4.3 验收结果怎么判断

离线验收成功意味着：

- Python 环境和 Skill 分发脚本可运行。
- JSON 与 Markdown 报告能生成。
- 固定 fixture 得到预期结果。

它不意味着：

- 真实网站已经被抓取或正确渲染。
- Google 已经收录页面。
- 排名、自然流量或收入得到改善。

## 5. 第一次真实项目审计

第一次真实使用建议采用低风险的 `AUDIT`，先确认证据范围和主要阻断，再决定是否进入 `FIX`。

### 5.1 切换到目标项目

```bash
export TARGET_PROJECT="/path/to/company-site"
export SKILLS_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
cd "$TARGET_PROJECT"
```

确认这里是网站项目，而不是 Vibio 源码仓库：

```bash
pwd
git status --short --branch
```

### 5.2 可选：初始化项目状态

只有希望跨会话持久化项目状态，并且已经获得项目内写入授权时，才执行本节。只读审计不要求先初始化 `.vibio/`；如果不允许写入，直接跳到 5.3。

新项目初始化一次：

```bash
python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" init \
  --project-root . \
  --project-id company-site-seo \
  --site-url https://www.example.com/ \
  --market DE \
  --language de-DE
```

初始化后会创建：

```text
.vibio/state/project.json
.vibio/state/project.sha256
.vibio/state/changes.jsonl
.vibio/state/reviews.jsonl
```

已经存在 `.vibio/` 时不要重复初始化，改为验证和渲染：

```bash
python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" validate \
  --project-root .
python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" render \
  --project-root . --out .vibio/project.md
```

不要手改 `project.sha256`、`changes.jsonl` 或 `reviews.jsonl`。它们是带哈希链的机器真源，Markdown 才是人读派生视图。

### 5.3 使用这份首次审计提示词

替换方括号中的内容后发送给 Codex：

```text
请使用 vibio-seo，对当前项目做第一次只读 SEO 审计。

站点：https://www.example.com/
目标市场/语言：德国，de-DE
主要合格转化：符合 ICP 的产品询盘
本次范围：[全站 / 产品模板 / 指定 URL]
当前问题：[例如产品页自然曝光低]
可用证据：[代码、dist、sitemap、robots、GSC 导出等]

授权边界：
- 可以读取项目文件和我提供的数据；
- 可以联网读取公开页面和最新官方文档；
- 可以在 reports/ 生成 JSON/Markdown 报告；
- 可以写入项目内 .vibio/ 状态；
- 不要修改业务代码、CMS、生产配置或外部系统。

先确认项目根、证据模式和主工作模式，再开始审计。报告中区分事实与假设，给出主导约束、独立严重阻断、证据、影响、验证方式、限制和接下来三项行动。不要承诺排名或固定周期。
```

如果你不允许任何写入，把授权改成“只允许读取和在对话中回答，不创建报告或 `.vibio/`”。

### 5.4 第一次成功的验收标准

一份合格的首次结果应同时满足：

- 明确了目标项目、URL/模板范围、市场、语言和主转化。
- 明确证据模式是 HTTP 源码、静态构建还是浏览器 DOM，没有混称。
- 区分已观察事实、官方规则、第一方数据和待验证假设。
- 给出当前资源焦点，并单独暴露访问、索引、安全、人工处置或重大转化阻断。
- 每个高影响发现有具体证据、位置、影响、置信度和复验方式。
- 没有超出授权修改代码、部署、发送外联或操作广告。
- 明确当前不能知道什么，以及如何补证据。
- 给出接下来三项可执行行动，而不是泛泛说“持续优化”。

## 6. 明确授权边界

不要只写“可以操作”或“只读”，应分别说明下面六类权限：

| 权限 | 示例 | 是否会改变状态 |
|---|---|---|
| 读取本地证据 | 代码、构建目录、CSV、历史报告 | 否 |
| 生成本地报告 | 在 `reports/` 写 JSON/Markdown | 是，本地文件写入 |
| 写项目状态 | 初始化或追加 `.vibio/` | 是，本地文件写入 |
| 修改业务产物 | 改代码、模板、配置或 CMS 导出 | 是，需要明确 FIX 授权 |
| 读取公开外部信息 | 抓取公开 URL、查看官方文档和 SERP | 通常无外部写入，但需要联网授权 |
| 外部副作用 | 部署、提交 GSC 设置、发送外联、启动广告、花费预算 | 是，必须单独明确授权 |

推荐使用三档模板：

只诊断：

```text
只读审计。可以读取文件和公开 URL，但不要创建文件、修改代码、写 .vibio 或操作外部系统。
```

诊断并记录：

```text
可以读取证据，并在 reports/ 和 .vibio/ 写入本项目报告与状态；不要修改业务代码或操作外部系统。
```

直接修复：

```text
可以在当前代码库内实施并验证修复，也可以更新 reports/ 和 .vibio/；不要部署生产、修改第三方账号、发送外联或启动广告。
```

AUDIT 请求本身不等于代码修改授权。即使你写了“全面检查”，Agent 也应在修改前确认是否进入 FIX。

## 7. 选择八种工作模式

不确定时总是先用 `vibio-seo`。已经清楚当前阶段时，再直接调用专项 Skill。

| 你现在的问题 | 模式 | 直接调用 | 输入重点 | 主要交付 |
|---|---|---|---|---|
| 不知道先做什么 | PLAN | `vibio-plan` | 业务目标、资源、数据、约束 | Now/Next/Later/Reject、依赖、指标、停止条件 |
| 不知道问题在哪里 | AUDIT | `vibio-audit` | URL/代码/构建/DOM、市场、转化 | 有证据的发现、严重阻断、复验方式 |
| 已知问题并要求直接修改 | FIX | `vibio-fix` | 代码库、技术栈、写权限、完成定义 | 已修改文件、构建/渲染验证、回退条件 |
| 不知道买家真实搜索什么 | KEYWORD | `vibio-keyword` | 国家、语言、GSC/RFQ/CRM/广告搜索词 | 词族、意图、受众、页面映射、拒绝项 |
| 已验证词族，要创建页面 | WRITE | `vibio-content` | SERP、企业事实、专家材料、来源 | 有差异化价值的页面成稿和证据账本 |
| 要修内链或获取正当外链 | LINK | `vibio-link` | 页面库存、链接数据、真实关系和资产 | 内链修复、人工审核前的外联计划 |
| 改动后要判断效果 | REVIEW | `vibio-review` | 准确变更日期、可比窗口、GSC/GA4/CRM | 产物、抓取/索引、搜索和业务分层结论 |
| 已确认流量或收录显著异常 | RECOVER | `vibio-seo` | 异常范围、历史、变更、manual action/安全信息 | 原因树、可逆修复、观察和停止条件 |

常用直接提示：

```text
请使用 vibio-plan，把当前证据转成可执行路线，不要用固定周数或承诺排名。
```

```text
请使用 vibio-keyword，针对德国 de-DE 市场验证真实买家用语。不要直译关键词，也不要编搜索量或 KD。
```

```text
请使用 vibio-review，读取 .vibio 里的准确变更日期后再选可比窗口；数据不成熟时明确说还太早。
```

RECOVER 只用于已验证的显著下滑，不应用来包装普通“曝光较低”的审计。

## 8. 选择正确的证据输入

| 你手上的材料 | 应采用的证据模式 | 能证明什么 | 不能证明什么 |
|---|---|---|---|
| 只有公开 URL | `--start-url` HTTP 源码 | HTTP 状态、源码中的 canonical/robots/链接等 | JavaScript 执行后的 DOM、真实收录或排名 |
| 网站代码库 | 栈识别 + 构建 + 文件检查 | 模板和配置实现 | 生产部署状态、Google 处理结果 |
| `dist/` 静态构建 | `--site-dir` | 生成 HTML、站内链接和本地图片引用 | HTTP 响应、浏览器运行时、收录 |
| 浏览器导出 DOM | `--rendered-dom` + provenance | 采集时浏览器 DOM 及与初始源码的差异 | 后续抓取、索引、排名 |
| GSC 常规导出 | `gsc_compare.py` | 同口径窗口的 clicks、impressions、CTR、position 变化 | 单个修改的因果效果、查询级收入 |
| GSC 生成式 AI 报告 | `gsc_ai_compare.py` | AI 报告中的 impressions 变化 | 查询、点击、CTR、引用、转化或增量 |
| GSC + GA4 + CRM 聚合 | `measurement_review.py` | 落地页/国家等共享粒度的方向性业务复盘 | 用户级路径或查询到收入的确定归因 |

`seo_inspect.py --start-url` 不执行 JavaScript，并拒绝 localhost、私网、链路本地、混合公网/私网 DNS 以及转向私网的重定向。本机开发站请使用静态构建或浏览器导出，不要试图绕过安全门禁。

## 9. 四条常用工作流

### 9.1 技术 SEO：AUDIT -> FIX -> REVIEW

第一步，诊断：

```text
请使用 vibio-seo 审计产品模板。先检查访问、索引资格、HTTP/静态构建/浏览器 DOM 差异、canonical、hreflang、结构化数据和内链。只诊断并写报告，不改代码。
```

第二步，明确授权后修复：

```text
请根据刚才确认的 High 发现进入 FIX。可以修改当前代码库，但不要部署。每项修改都要运行项目现有 build/lint/test，并用同一范围重新生成 SEO 产物报告；把即时产物验证和仍需等待的搜索结果分开。
```

第三步，部署或发布后验证产物：

- 检查生产 HTTP 状态、canonical、robots、结构化数据和代表性浏览器 DOM。
- 记录部署时间、受影响 URL、before/after 报告和回退条件。
- 产物未正确发布时，结论是 `implementation-failed`，不能进入效果判断。

第四步，数据成熟后复盘：

```text
请使用 vibio-review。读取 .vibio 中这次修改的准确日期，先判断抓取、索引和数据窗口是否成熟，再比较同口径 GSC/GA4/CRM。不要把相关变化写成因果；没有合格对照时最高只给方向性结论。
```

### 9.2 需求与内容：KEYWORD -> WRITE -> LINK

关键词验证：

```text
请使用 vibio-keyword。目标市场是德国，语言 de-DE，买家是工业采购和工程团队，主转化是有效 RFQ。结合 GSC、CRM/RFQ、可用广告搜索词和德国 SERP 验证查询族、搜索者身份、任务和收入路径。保留 reject 词及原因，不要用英文直译或虚构搜索量。
```

内容生产：

```text
请使用 vibio-content。只为已经通过验证的查询族创建页面。先列出需要企业专家补充的一手事实和来源，再建立证据账本、非同质化贡献和页面结构；没有真实材料时不要虚构案例、认证或性能数字。
```

内部发现与外部佐证：

```text
请使用 vibio-link。先修复新页面的站内发现路径、相关 donor 页面和用户路径，再基于真实关系或可链接资产准备外联。外部发送最多推进到 pending-human-review，不要自动发送。
```

### 9.3 搜索到业务：REVIEW

准备同口径数据：

- GSC 使用页面级聚合；如使用 query，不能与 GA4/CRM 做确定性查询级收入连接。
- GA4 使用 landing page 聚合，并记录 property 时区、采样、阈值和归因模型。
- CRM 只导出日期、落地页、国家和聚合指标，不含姓名、邮箱、电话或 lead ID。
- 所有来源记录 `data_as_of`、finality、分页、行数限制和数据质量。

推荐提示：

```text
请使用 vibio-review 复盘这次产品页改版。先核对实施是否持续存在，再分别评估抓取/索引、GSC 搜索表现、GA4 有效会话和 CRM 合格询盘。以落地页或意图集群为连接单位，不做查询级收入归因；缺值不要补 0。
```

### 9.4 异常恢复：RECOVER

先确认异常是真实的：

- 比较相同 property、search type、市场、设备、页面范围和日期口径。
- 排除导出不完整、埋点变化、迁移、季节性和需求变化。
- 检查 manual action、安全问题、robots/noindex、canonical、状态码和模板部署。

推荐提示：

```text
请使用 vibio-seo 的 RECOVER 模式。GSC 显示从 [日期] 起 [范围] 的 clicks/impressions 显著下降。先验证数据口径和异常范围，再检查技术回归、manual action/安全、迁移、意图、竞争/SERP 变化和 Google 更新时间线。时间重合不要直接写成因果，优先提出可逆且有机制证据的动作。
```

## 10. 手动运行六个确定性工具

这是进阶参考。大多数用户完成第 1-9 节后，直接让 Agent 选择和解释工具即可；只有接入 CI、独立复验或调试输入合同时才需要阅读本节。

下面假设已经安装所有普通用户 Skill：

```bash
export SKILLS_ROOT="${CODEX_HOME:-$HOME/.codex}/skills"
```

### 10.1 `seo_inspect.py`：HTML 和链接产物检查

三种输入只能选择一种。

静态构建：

```bash
python "$SKILLS_ROOT/vibio-audit/scripts/seo_inspect.py" \
  --site-dir dist \
  --base-url https://www.example.com/ \
  --sitemap dist/sitemap.xml \
  --robots public/robots.txt \
  --production \
  --json-out reports/audit.json \
  --markdown-out reports/audit.md
```

有限公网 HTTP 源码抓取：

```bash
python "$SKILLS_ROOT/vibio-audit/scripts/seo_inspect.py" \
  --start-url https://www.example.com/ \
  --max-pages 100 \
  --timeout 15 \
  --production \
  --json-out reports/http-audit.json \
  --markdown-out reports/http-audit.md
```

浏览器 DOM 与初始源码比较：

```bash
python "$SKILLS_ROOT/vibio-audit/scripts/seo_inspect.py" \
  --rendered-dom evidence/rendered \
  --source-input evidence/source \
  --browser-provenance evidence/browser-provenance.json \
  --base-url https://www.example.com/ \
  --json-out reports/browser-dom.json \
  --markdown-out reports/browser-dom.md
```

provenance 最小结构：

```json
{
  "schema_version": "1.0",
  "capture_method": "Playwright page.content()",
  "browser": "Chromium 140",
  "captured_at": "2026-07-11T10:00:00+08:00",
  "javascript_enabled": true,
  "documents": [
    {
      "url": "https://www.example.com/product/",
      "sha256": "<对应 DOM 文件的 64 位 SHA-256>"
    }
  ]
}
```

先计算每个 DOM 文件的真实 SHA-256，再填入 provenance：

```bash
python -c 'from pathlib import Path; import hashlib; p=Path("evidence/rendered/product.html"); print(hashlib.sha256(p.read_bytes()).hexdigest())'
```

`--fail-on high` 适合 CI：命中 High 或 Critical 时报告仍会写出，但进程退出码为 `2`。`--production` 是“输入确实代表生产目标”的声明，不是普通的严格模式。

### 10.2 `gsc_compare.py`：常规 GSC 窗口比较

单文件必须有 Date/日期列：

```bash
python "$SKILLS_ROOT/vibio-review/scripts/gsc_compare.py" \
  --input data/gsc.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example.com \
  --search-type web \
  --analysis-timezone Asia/Shanghai \
  --source-timezone America/Los_Angeles \
  --data-as-of 2026-07-05T12:00:00Z \
  --finality final \
  --no-row-limit-hit \
  --pagination-complete \
  --data-quality complete \
  --filter-notes "country=DE; device=all" \
  --json-out reports/gsc-review.json \
  --markdown-out reports/gsc-review.md
```

也可以用 `--baseline before.csv --current after.csv` 双文件模式。两期的 property、search type、维度、过滤条件和来源日界必须一致。`--allow-unaligned-overall` 只允许探索性的总体描述，不会让不可比 cohort 变得可比。

`data_as_of` 必须是带 UTC offset 的 ISO 8601 时间，例如 `2026-07-05T12:00:00Z` 或 `2026-07-05T20:00:00+08:00`，不能只写日期。

### 10.3 `gsc_ai_compare.py`：GSC 生成式 AI 展示报告

```bash
python "$SKILLS_ROOT/vibio-review/scripts/gsc_ai_compare.py" \
  --input data/gsc-ai.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example.com \
  --filters "country=DE" \
  --data-as-of 2026-07-05T12:00:00Z \
  --finality final \
  --completeness complete \
  --no-row-limit-hit \
  --json-out reports/gsc-ai.json \
  --markdown-out reports/gsc-ai.md
```

只允许日期、页面、国家/地区、设备和展示次数。Query、Clicks、CTR、Position、Citation、Conversion 或 Revenue 列会被拒绝。该报告是普通 Web Performance 的非可加子集，不能与 Web 总数相加。

### 10.4 `measurement_review.py`：GSC、GA4、CRM 聚合复盘

```bash
python "$SKILLS_ROOT/vibio-review/scripts/measurement_review.py" \
  --gsc-page data/gsc-page.csv \
  --ga4 data/ga4-landing.csv \
  --crm data/crm-cohort.csv \
  --mapping data/measurement.json \
  --json-out reports/business-review.json \
  --markdown-out reports/business-review.md
```

CSV 推荐粒度：

```text
GSC: Date,Page,Country,Device,Clicks,Impressions
GA4: Date,Landing page,Country,Device,Sessions,Conversions
CRM: Date,Landing page,Country,Leads,Qualified,Pipeline value
```

<details>
<summary>展开完整 measurement.json 示例</summary>

完整 `measurement.json` 示例：

```json
{
  "windows": {
    "baseline": {"start": "2026-05-01", "end": "2026-05-31"},
    "current": {"start": "2026-06-01", "end": "2026-06-30"}
  },
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
  },
  "property": "sc-domain:example.com",
  "search_type": "web",
  "dimension_mapping": {
    "gsc_page": {
      "date": "Date",
      "landing_page": "Page",
      "country": "Country",
      "device": "Device"
    },
    "ga4": {
      "date": "Date",
      "landing_page": "Landing page",
      "country": "Country",
      "device": "Device"
    },
    "crm": {
      "date": "Date",
      "landing_page": "Landing page",
      "country": "Country"
    }
  },
  "metric_mapping": {
    "crm": {
      "leads": "Leads",
      "qualified": "Qualified",
      "pipeline_value": "Pipeline value"
    }
  },
  "value_mapping": {
    "country": {"DEU": "de", "Germany": "de"},
    "device": {"DESKTOP": "desktop", "desktop": "desktop"}
  },
  "url_normalization": {
    "base_url": "https://www.example.com/",
    "force_https": true,
    "strip_query": true,
    "strip_fragment": true,
    "lowercase_host": true,
    "trailing_slash": "remove",
    "mappings": {"/old-product/": "/product/"}
  },
  "crm_definition": {
    "stage": "sales accepted",
    "qualified": "meets ICP and product need"
  }
}
```

</details>

不要把 GSC Query、邮箱、电话、用户 ID、lead ID、account ID 或 CRM 原始个人行放进这些文件。缺值不会自动补 0，最高自动结论仅为方向性描述。

### 10.5 `experiment.py`：页面级对照实验

只有在实施前能够冻结足够同类页面、主指标、护栏、窗口和测量口径时才使用。纯前后比较不是本工具支持的实验设计。

冻结计划：

```bash
python "$SKILLS_ROOT/vibio-plan/scripts/experiment.py" plan \
  --spec .vibio/experiments/title-test/spec.json \
  --baseline .vibio/experiments/title-test/baseline.csv \
  --out-dir .vibio/experiments/title-test/frozen
```

生成 `plan.json` 和 `assignments.csv`。冻结目录不可覆盖；重做实验应使用新的实验 ID 和目录。

窗口成熟后分析：

```bash
python "$SKILLS_ROOT/vibio-review/scripts/experiment.py" analyze \
  --plan .vibio/experiments/title-test/frozen/plan.json \
  --panel .vibio/experiments/title-test/panel.csv \
  --artifact-report .vibio/experiments/title-test/artifact.json \
  --measurement-metadata .vibio/experiments/title-test/measurement-metadata.json \
  --out .vibio/experiments/title-test/result.json \
  --markdown-out
```

输入职责：

| 文件 | 内容 |
|---|---|
| `spec.json` | 实验 ID、`randomized_page_holdout` 或 `matched_page_did`、单位列、主指标、护栏、seed、窗口、MDE、alpha 和来源口径 |
| `baseline.csv` | 每个候选页面实施前的主指标和护栏摘要 |
| `panel.csv` | 每个页面在基线和观察窗口内的日期、分组、指标、污染和实施状态 |
| `artifact.json` | plan hash、实现是否通过及具体产物证据 |
| `measurement-metadata.json` | 数据截止、finality、分页、触限、采样、阈值和归因元数据 |

仓库目前没有可直接运行的完整实验 fixture，因为 panel 必须来自真实冻结分组和完整日期窗口。首次使用时让 `vibio-plan` 根据项目数据生成 `spec.json` 和 `baseline.csv`，人工确认后再冻结；让 `vibio-review` 检查 panel、artifact 和 measurement metadata 的字段及口径后再分析。不要手写一套“看起来能通过”的实验数据来支持业务结论。

`eligible_incremental` 只表示自动完整性检查允许人工做增量解读，不等于效果为正，更不等于排名、流量或收入因果已经成立。

### 10.6 `state_manager.py`：可验证项目状态

初始化、验证和渲染：

```bash
python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" init \
  --project-root . --project-id example-seo \
  --site-url https://www.example.com/ --market DE --language de-DE

python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" validate \
  --project-root .

python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" render \
  --project-root . --out .vibio/project.md
```

最小 planned 事件文件：

```json
{
  "change_id": "change-001",
  "status": "planned",
  "summary": "修复产品模板 canonical"
}
```

追加事件：

```bash
python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" append-change \
  --project-root . --input change.json
```

主状态链为：

```text
planned -> implemented -> artifact_verified -> outcome_pending -> reviewed
```

`artifact_verified` 必须带 `artifact_verification.passed=true` 和非空证据。不要跳过产物验证直接声称结果有效。

如果正式实验结果可能支持 `no-detectable-change`，不能手写 power。生成确定性 detectability 证据：

```bash
python "$SKILLS_ROOT/vibio-memory/scripts/state_manager.py" detectability \
  --project-root . \
  --experiment-plan .vibio/experiments/title-test/frozen/plan.json \
  --experiment-result .vibio/experiments/title-test/result.json \
  --out .vibio/experiments/title-test/detectability.json
```

只有所有测量完整性门禁通过、power >= 0.8 且正式报告置信区间包含 0 时，该证据才有资格支持 `no-detectable-change`；这仍不证明效果绝对为零。

## 11. 理解报告与效果结论

Vibio 把“修好了”拆成四层，不能越级：

| 层级 | 要回答的问题 | 常见证据 |
|---|---|---|
| 产物 | 修改是否真实存在且没有破坏页面 | build、lint、test、HTML、DOM、Schema、HTTP |
| 抓取/索引 | 搜索引擎是否能访问、选择并处理页面 | GSC URL Inspection、覆盖/页面索引、日志、sitemap |
| 搜索表现 | 可见性和有效自然流量是否变化 | 同口径 GSC、可比 cohort、成熟窗口 |
| 业务结果 | 合格会话、线索、销售管道是否变化 | GA4/CRM 聚合、预注册实验 |

常见 REVIEW 结论：

| 结论 | 含义 |
|---|---|
| `implementation-failed` | 修改未正确部署或产物验证失败 |
| `not-yet-observable` | 产物正确，但抓取、索引或数据窗口尚未成熟 |
| `directional-positive` | 描述性数据方向积极，但不能做因果声明 |
| `incremental-positive` | 合格预注册设计支持范围明确的正向增量解释 |
| `no-detectable-change` | 设计有足够检测能力且区间包含 0，未检测到预注册 MDE 级别效果；不等于绝对零效果 |
| `negative-or-regression` | 实施或结果出现负向变化，需要停止、回退或进一步诊断 |
| `inconclusive` | 数据、口径、实现、污染、采样或完整性不足以判断 |

修复完成后立即得到的通常只是“产物通过”，不是“SEO 已生效”。

## 12. 数据、隐私和安全边界

### 可以提供

- 聚合到页面、日期、国家、设备或意图集群的 GSC/GA4/CRM 数据。
- 匿名化的 RFQ 用语和客户任务摘要。
- 公开页面、构建产物、sitemap、robots 和浏览器 DOM。
- 不含凭据的配置、部署记录和变更日期。

### 不要提供或写入 `.vibio/`

- API key、密码、Cookie、session、私钥或带认证参数的 URL。
- 姓名、邮箱、电话、身份证号、lead ID、account ID 或联系人名单。
- CRM 原始个人记录和用户级访问路径。
- 未经授权的生产凭据或第三方账号访问。

### 外部操作边界

- LINK 可以准备外联材料，但最多推进到 `pending-human-review`；由人类审核和发送。
- 广告搜索词、Planner 和落地页实验可用于验证需求、措辞和页面承诺；广告支出不是自然排名因素。
- 不自动启动 Campaign、调整预算或花费广告资金。
- 不自动部署生产、提交 GSC 变更或修改第三方账号，除非用户明确授权该具体动作。
- 不购买、自动生成或伪装用于操纵排名的链接。

## 13. 常见问题排查

| 症状 | 常见原因 | 处理方法 |
|---|---|---|
| Codex 没有使用 Vibio | Skill 目录未被重新加载，或请求过于泛化 | 新开会话；确认 `SKILLS_ROOT/vibio/SKILL.md` 存在；显式说“请使用 `vibio-seo`” |
| `Python 3.x` 版本过低 | 系统 Python 不是 3.10+ | 安装新版本并重新创建 `.venv` |
| `ModuleNotFoundError` | 未激活 venv 或未安装项目依赖 | `source .venv/bin/activate` 后运行 `python -m pip install -e '.[dev]'` |
| 严格校验提示生成副本漂移 | 直接修改了子 Skill 的生成文件 | 只改顶层 `references/`、`runtime/`、`schemas/` 或 `SKILL.md`，再运行 `build_skills.py --clean` |
| `data_as_of` 报 UTC offset 错误 | 只写了 `YYYY-MM-DD` | 改为 `2026-07-05T12:00:00Z` 这类完整时间戳 |
| 在线抓取拒绝 localhost 或私网 | SSRF 安全门禁正常工作 | 改用 `--site-dir` 或浏览器导出 DOM，不要绕过门禁 |
| 在线报告看不到 JS 内容 | 内置 HTTP 抓取器不执行 JavaScript | 提供带 provenance 的浏览器 DOM，并与初始源码配对 |
| GSC 比较拒绝两期文件 | 维度、过滤条件、property、search type 或窗口不一致 | 重新导出同口径数据；不要用强制参数掩盖差异 |
| GSC 报告为 `inconclusive` | finality、分页、行数限制、时区或质量声明不完整 | 补齐真实元数据；未知就保留 unknown，不要猜测 |
| AI 报告字段被拒绝 | 把普通 Web 或自定义“引用”列交给 AI 解析器 | AI 工具只接受 Date/Page/Country/Device/Impressions |
| 业务复盘拒绝 CRM | 含 Query、邮箱、电话或用户/线索 ID | 在源系统先聚合到日期 + 落地页 + 国家，再导出 |
| 实验不能覆盖 frozen 目录 | 冻结计划有意防止事后改写 | 使用新的实验 ID 和目录；不要覆盖旧计划 |
| `eligible_incremental=true` 但没有正向结论 | 它只表示有资格人工解读 | 检查主指标方向、区间、护栏、机制和适用范围 |
| `.vibio` 验证失败 | 手改了 JSONL、hash 或非法跳状态 | 停止继续写入，保留原文件，根据最后一个有效链 head 恢复；不要重算 hash 掩盖改写 |
| 修复后暂时看不到流量变化 | 抓取/索引或观察窗口未成熟 | 标为 `not-yet-observable`，按预先定义的复核点等待，不要反复改页面 |

查看六个脚本的顶层帮助：

```bash
python "$SKILLS_ROOT/vibio/scripts/seo_inspect.py" --help
python "$SKILLS_ROOT/vibio/scripts/gsc_compare.py" --help
python "$SKILLS_ROOT/vibio/scripts/gsc_ai_compare.py" --help
python "$SKILLS_ROOT/vibio/scripts/measurement_review.py" --help
python "$SKILLS_ROOT/vibio/scripts/experiment.py" --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" --help
```

`experiment.py` 和 `state_manager.py` 使用子命令；完整参数还要查看对应子命令帮助：

```bash
python "$SKILLS_ROOT/vibio/scripts/experiment.py" plan --help
python "$SKILLS_ROOT/vibio/scripts/experiment.py" analyze --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" init --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" append-change --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" append-review --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" validate --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" render --help
python "$SKILLS_ROOT/vibio/scripts/state_manager.py" detectability --help
```

## 14. 升级、卸载和开发者验证

### 14.1 升级

1. 在 `VIBIO_REPO` 获取或切换到目标版本。
2. 重新创建/激活 Python 环境并安装依赖。
3. 运行构建、严格校验、测试和离线合同回归。
4. 备份或移走旧安装目录，再复制新的 Skill 目录。
5. 新开客户端会话。
6. 在真实项目先运行 `.vibio` validate，再继续任务。

不要用旧版生成 references/scripts 与新版 `SKILL.md` 混装。

### 14.2 卸载

从客户端的 `SKILLS_ROOT` 移除已安装的 `vibio*` Skill 目录即可。不要因此删除真实项目内的 `.vibio/`，它属于项目历史，应按项目的数据保留策略处理。

### 14.3 开发者硬闸门

修改顶层真源或 Skill 后，在 `VIBIO_REPO` 按顺序执行：

```bash
python scripts/build_skills.py --clean
python scripts/validate_repo.py --strict
pytest -q
python scripts/eval_runner.py --strict
git diff --check
```

各子 Skill 下的 `references/`、`scripts/` 和 `schemas/` 是生成副本。不要直接编辑；应修改顶层真源，再重新构建。

这些闸门证明仓库结构、工具合同和 fixture 没有回归，不证明真实模型行为或真实 SEO 结果。真实质量仍需要同提示运行、人工评审和站点级复盘。

## 15. 最终检查清单

### 安装完成

- [ ] Python 版本为 3.10+。
- [ ] `build_skills.py --clean` 成功。
- [ ] `validate_repo.py --strict` 为 0 errors、0 warnings。
- [ ] Skill 目录位于客户端 `SKILLS_ROOT` 的直接子目录。
- [ ] 已新开客户端会话并能显式触发 `vibio-seo`。

### 项目开工

- [ ] 已确认 `TARGET_PROJECT`，没有在 Skill 仓库里创建真实 `.vibio/`。
- [ ] 已提供站点、市场、语言、主转化和当前目标。
- [ ] 已分别声明读取、报告、状态、代码、联网和外部操作权限。
- [ ] 已说明当前可用和不可用的数据。

### 每次交付

- [ ] 主导约束和独立严重阻断有证据。
- [ ] 事实、规则、第一方数据、实验和假设已区分。
- [ ] 已实施变更与当前验证清楚分开。
- [ ] 产物、抓取/索引、搜索表现和业务结果没有混为一谈。
- [ ] 没有编造搜索量、KD、排名、外链、转化或收入。
- [ ] 广告数据没有被写成自然排名因素。
- [ ] 风险、缺失数据、观察窗口和停止条件明确。
- [ ] 给出接下来三项行动。
- [ ] 只有在授权范围内才更新 `.vibio/`。

最稳妥的默认入口始终是：

```text
请使用 vibio-seo。先读取当前项目和已有 .vibio 状态，确认目标、证据范围、权限和主工作模式，然后继续执行，不要只给通用清单。
```
