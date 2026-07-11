# Vibio SEO v5

Vibio SEO 是一组证据驱动、可执行、可复盘的搜索优化 Skill。它面向真实网站、代码库和业务数据工作：先找当前资源焦点并暴露独立严重阻断，再选择最可能改变目标指标的行动；在用户授权范围内实施，验证渲染产物，并在搜索引擎重新抓取后复测结果。

默认使用中文沟通、分析和交付报告。面向目标市场的页面正文、metadata 与广告实验素材仍按该市场的真实语言制作，不能把中文或英文词表直接翻译成海外关键词。

当前版本为 `5.0.0`。

## SEO 成果边界

Vibio 的目标不是生成一份通用检查清单，而是持续改善以下可控环节：

- 抓取、渲染、索引资格与重复 URL 管理。
- 目标市场的真实需求、搜索意图与页面映射。
- 页面独特价值、事实可信度、专业经验和任务完成度。
- 内部发现路径、正当外部权威与品牌需求。
- 自然搜索落地页的有效流量、合格线索和销售管道测量。

它能保证的是证据分级、明确决策、可验证产物、停止条件和复盘闭环，不能保证具体排名、流量增幅、AI 引用、收入或固定见效时间。构建成功只证明产物存在；收录、排名与业务结果必须在适合该站点和查询的观察窗口中，用第一方数据验证。

每项实质性任务都应交付：资源焦点与独立严重阻断的证据、已实施变更或决策、当前验证结果、后续指标与观察窗口、风险和缺失数据、接下来三项行动，以及已更新的 `.vibio/` 状态。

## 架构

```text
vibio_seo/
├── vibio.manifest.yaml       # Skill 注册表、引用策略、外部能力与 fallback
├── vibio/SKILL.md            # vibio-seo 主路由器
├── vibio-*/SKILL.md          # 专项 Skill
├── references/               # 唯一人工维护的参考资料真源
├── runtime/                  # 唯一人工维护的确定性运行工具真源
├── schemas/                  # 运行工具 JSON 输出契约真源
├── scripts/build_skills.py   # 生成各 Skill 的自包含 references、工具与 Schema
├── scripts/validate_repo.py  # 仓库、依赖、引用和 eval 严格校验
├── scripts/eval_runner.py    # 可重复的离线合同回归，不执行真实 Skill
├── evals/schema/             # eval JSON Schema
└── tests/                    # 校验器测试
```

主路由器支持 `PLAN`、`AUDIT`、`FIX`、`WRITE`、`KEYWORD`、`LINK`、`REVIEW`、`RECOVER` 八种模式。`RECOVER` 由 `vibio-seo` 按恢复手册执行，当前没有单独的 `vibio-recover` 目录。

| Skill | 职责 |
|---|---|
| `vibio-seo` | 识别资源焦点与独立严重阻断，选择并继续执行模式，串联如 `AUDIT -> FIX -> REVIEW` 的完整闭环 |
| `vibio-plan` | 在项目适合的决策窗口内制定依赖路线、产能安排、指标和停止条件 |
| `vibio-audit` | 对代码、渲染 HTML 或 URL 做首次诊断，区分事实与假设并形成可验证发现 |
| `vibio-fix` | 识别技术栈，修改代码、CMS 或配置，并在 HTTP 响应和渲染产物中验证 |
| `vibio-keyword` | 从目标市场真实用语和需求证据出发，验证意图、受众和商业路径，完成词族到页面映射 |
| `vibio-content` | 逆向真实 SERP，收集一手材料和来源，产出有非同质化价值的页面成稿并接受对抗审查 |
| `vibio-link` | 修复内部发现与权重传递，通过真实资产、关系、PR 和定向外联获取正当编辑型链接 |
| `vibio-review` | 读取准确变更历史，复测产物、抓取/索引、搜索可见性、有效流量和业务结果 |
| `vibio-memory` | 定义项目根 `.vibio/` 的状态、tracker、changelog 与跨会话读写约定 |
| `vibio-factory` | 创建或改进 Vibio 专项 Skill，维护触发、引用、评测和系列一致性 |

## 证据政策

所有高影响建议、数值论断和预算决策都遵循 [references/evidence-policy.md](references/evidence-policy.md)：

1. E1：最新官方规则、资格要求或产品文档。
2. E2：目标企业或网站的 GSC、分析平台、CRM、日志、Merchant Center 等第一方数据。
3. E3：目标网站或市场中的受控实验。
4. E4：当前 SERP/网站观察，或注明日期、样本、市场和方法的第三方研究。
5. E5：待验证假设。

E1 用于判断政策和资格，E2 用于确定项目优先级。E3-E5 不能伪装成普遍排名规则，只能形成边界明确的实验或建议。易变事项在执行前重新核验实时官方文档，并记录 `verified_on`、规范 URL、置信度和适用范围。

不得虚构搜索量、KD、排名、外链、转化率或收入。不得把相关性研究改写成排名因果，也不得用无来源的固定 CTR、转化率、锚文本比例、品牌提及倍数或 AI 引用增幅。

## 广告数据只服务 SEO

付费搜索可以缩短 SEO 学习周期，但广告支出不是自然排名因素。只有当实验能回答一个明确 SEO 决策时才进入 Vibio 范围，例如：

- 用 Keyword Planner、真实 search terms 和目标市场定向验证买家措辞与无效受众。
- 比较页面承诺、标题表达或落地页对合格线索的影响。
- 用 paid and organic report 观察覆盖重叠并形成蚕食或增量假设；因果结论另用预先设计的开关或 holdout 实验验证。
- 将广告搜索词和有效线索反馈给关键词验证、页面映射与内容优先级。

广告竞争程度和 CPC 不能称为 organic KD；付费流量表现也不能证明同一页面会获得自然排名。没有转化测量、目标市场控制、预先定义的决策规则和停止条件时，不建议为 SEO 启动投流。泛 Campaign 搭建、出价和预算优化不属于本项目范围。

## 外部能力与降级

`vibio.manifest.yaml` 中声明的 `seo-*` 与 `b2b-seo` 都是可选能力，不是运行前置条件。能力可用时使用其数据；不可用时必须执行对应 fallback，例如：

- SERP 数据不可用：使用带目标市场和日期的人工样本，或请用户提供导出。
- 抓取工具不可用：从 sitemap 发现 URL，再做范围明确的 `curl`、浏览器或本地抓取。
- GSC/GA4/CRM 不可用：定义测量方案，并明确哪些结论当前无法得出。
- 关键词工具不可用：使用第一方查询、RFQ/CRM、本地语言语料和免费 SERP 证据，但不编搜索量或难度。
- 外链平台不可用：使用可获得的引用域导出和人工核验，不虚构权威指标或毒链结论。

工作流不能只推荐某个外部提供商后停止。即使未安装任何外部能力，也要继续完成一个范围明确、诚实标注限制的版本。

## 引用真源与构建

顶层 `references/` 是唯一人工维护的参考资料真源。各 Skill 下的 `references/` 是构建产物，用于让每个 Skill 在独立安装后仍能解析本地引用：

- `vibio/` 获得完整参考资料包。
- 其他专项 Skill 只获得从其 `SKILL.md` 开始递归计算的引用闭包。
- `.vibio-generated.json` 记录生成器、Skill 和每个文件的 SHA-256。
- 不要直接编辑子 Skill 下的引用副本；修改顶层真源后重新构建。

```bash
python scripts/build_skills.py --clean
```

只重建一个专项 Skill：

```bash
python scripts/build_skills.py --clean --skill vibio-content
```

`--clean` 会删除不再属于该 Skill 引用闭包的旧副本。严格校验会检测缺失引用、生成副本漂移、未声明外部能力、过时禁用路径、frontmatter 以及 eval schema。

## 自带运行工具

构建器还会把 `runtime/` 唯一真源中的脚本复制到需要它们的 Skill 的 `scripts/`，把 `schemas/` 中相应的 Draft 2020-12 JSON Schema 复制到 `schemas/`，并分别记录 SHA-256。严格校验会阻止脚本或 Schema 缺失、篡改及与真源漂移，因此独立安装 `vibio-audit`、`vibio-review` 等目录后仍可执行。

静态构建检查（不会执行 JavaScript）：

```bash
python vibio-audit/scripts/seo_inspect.py \
  --site-dir dist --base-url https://example.com/ \
  --sitemap dist/sitemap.xml --robots public/robots.txt \
  --json-out audit.json --markdown-out audit.md
```

浏览器导出 DOM 与初始源码对比：

```bash
python vibio-audit/scripts/seo_inspect.py \
  --rendered-dom evidence/rendered --source-input evidence/source \
  --browser-provenance evidence/browser-provenance.json \
  --base-url https://example.com/ \
  --json-out browser-dom.json --markdown-out browser-dom.md
```

GSC CSV 同口径窗口对比：

```bash
python vibio-review/scripts/gsc_compare.py \
  --input gsc.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example.com --search-type web \
  --analysis-timezone Asia/Shanghai \
  --source-timezone America/Los_Angeles \
  --data-as-of 2026-07-05T12:00:00Z --finality final \
  --no-row-limit-hit --pagination-complete --data-quality complete \
  --json-out gsc-review.json --markdown-out gsc-review.md
```

GSC 生成式 AI 效果报告只含展示次数，使用独立解析器：

```bash
python vibio-review/scripts/gsc_ai_compare.py \
  --input gsc-ai.csv \
  --baseline-start 2026-05-01 --baseline-end 2026-05-31 \
  --current-start 2026-06-01 --current-end 2026-06-30 \
  --property-id sc-domain:example.com --filters "country=DE" \
  --data-as-of 2026-07-05T12:00:00Z --finality final \
  --completeness complete --no-row-limit-hit \
  --json-out gsc-ai-review.json --markdown-out gsc-ai-review.md
```

这些报告是可复现证据，不是排名效果证明。`seo_inspect.py` 明确区分 `http_source`、`static_build` 和 `browser_dom`，并在静态构建中检查 `src`、`srcset`、`picture/source` 与常见 lazy 属性引用的站内图片文件；它的 HTTP 抓取器不会执行 JavaScript。远程抓取会拒绝本机、私网、链路本地和混合公网/私网 DNS 结果，连接固定到已校验公网 IP，并在每次重定向重新校验；robots 自动声明的 sitemap 及递归/重定向默认只允许站点同源，显式 `--sitemap` 才可授权跨源公网 URL。单响应默认上限为 20 MiB，可用 `--max-response-bytes` 收紧或显式调整，`Content-Length` 与实际读取均受门禁。外部浏览器 DOM 只有在 `--browser-provenance` 按 URL 和 SHA-256 绑定浏览器、采集时间与 JavaScript 状态后，才会标为客户端 DOM 已验证。机器报告中的本地输入只保留文件名或站点相对路径，并以 SHA-256 绑定内容，不保存本机绝对目录。工具不知道 Google-selected canonical、真实收录和搜索意图；`gsc_compare.py` 默认拒绝不同维度粒度，区分 analysis timezone 与 GSC 的 America/Los_Angeles 来源日界，并把数据截止/finality/分页/触限/质量声明不完整的报告降级为 `inconclusive`。`gsc_ai_compare.py` 只处理生成式 AI 报告 impressions；该报告是 Web Performance 的非可加子集，不能推断 query、click、CTR、引用或转化。所有前后变化都只能描述，合格因果结论仍需要预先设计的对照或实验。

兼容性：隐私与抓取边界对应 `seo_inspect` 1.3.0 / schema 1.3、`gsc_compare` schema 1.3.0、`gsc_ai_compare` schema 1.2、`measurement_review` 1.2.0 / schema 1.2。消费方若曾依赖报告中的本地绝对路径，应改用 `path`/`source` 文件引用加 SHA-256 定位输入；含高置信 PII 的 GSC query CSV 现在会拒绝生成报告；本机或私网站点应改用 `--site-dir`、`--rendered-dom` 等本地证据模式，不再通过 `--start-url` 抓取。

结构化项目状态：

```bash
python vibio-memory/scripts/state_manager.py init --project-root . \
  --project-id example-seo --site-url https://example.com/ \
  --market DE --language de-DE
python vibio-memory/scripts/state_manager.py validate --project-root .
python vibio-memory/scripts/state_manager.py render --project-root . \
  --out .vibio/project.md
```

`.vibio/state/project.json`、`project.sha256`、`changes.jsonl` 与 `reviews.jsonl` 是机器真源；Markdown 是派生人读视图。状态链绑定项目摘要和交叉链 head，并串行化并发追加，阻止静默改写历史、凭据/PII 写入和从“已修改”直接跳到“增量有效”。实验 change 必须在首条 `planned` 事件中提前绑定 plan 路径、文件 SHA-256 与 plan hash。写入 `incremental-positive` 或 `no-detectable-change` 还必须引用 status=complete、issues 为空的 `measurement_integrity`、同一冻结计划、正式实验报告及 SHA-256，并用 `experiment_inputs` 绑定 panel、artifact report 和可选 measurement metadata 的项目内路径/SHA-256。状态工具会用这些原始输入重跑分析，并将重放结果与正式报告除 `analyzed_at` 外整份比较，额外字段也会被拒绝；不接受只重算报告文件哈希的自洽改写。`no-detectable-change` 不接受手写 power；必须由 `state_manager.py detectability` 绑定冻结计划与正式报告生成证据，并在追加和校验状态时确定性重算。

GSC、GA4 与 CRM 聚合业务复盘：

```bash
python vibio-review/scripts/measurement_review.py \
  --gsc-page gsc-page.csv --ga4 ga4-landing.csv --crm crm-cohort.csv \
  --mapping measurement.json \
  --json-out business-review.json --markdown-out business-review.md
```

配置必须显式声明日期窗口、`analysis_timezone`、各来源 `source_timezones`、GSC property/search type、字段映射、URL 规范化和 CRM 合格定义。`source_metadata` 为每个来源保存 `source_kind`、`data_as_of`、finality/preliminary、row-limit/pagination、适用的 sampling/thresholding、data quality 和 attribution model。GSC 常规日数据使用 America/Los_Angeles，GA4 使用 property 时区，CRM 使用业务系统时区；只有 date 粒度且日界不同时，工具禁止逐日跨源 join，只保留各来源显式窗口汇总。`measurement_review.py` 拒绝 Query、用户/线索 ID、邮箱、电话与原始 CRM 行；`gsc_compare.py` 允许普通 query cohort，但在聚合前拒绝高置信邮箱、格式化电话、有效身份证号或带身份上下文的稳定 ID，且错误不回显原始值。缺值不补零，最高自动结论仅为方向性描述。元数据缺失、冲突、触限、采样、阈值或 preliminary 会降级为 `inconclusive`。机器输出遵循 `measurement_review.report.schema.json`。

页面级对照实验分为“实施前冻结”和“窗口成熟后分析”两步：

```bash
python vibio-plan/scripts/experiment.py plan \
  --spec .vibio/experiments/seo-title-2026-01/spec.json \
  --baseline .vibio/experiments/seo-title-2026-01/baseline.csv \
  --out-dir .vibio/experiments/seo-title-2026-01/frozen

python vibio-review/scripts/experiment.py analyze \
  --plan .vibio/experiments/seo-title-2026-01/frozen/plan.json \
  --panel .vibio/experiments/seo-title-2026-01/panel.csv \
  --artifact-report .vibio/experiments/seo-title-2026-01/artifact.json \
  --measurement-metadata .vibio/experiments/seo-title-2026-01/measurement-metadata.json \
  --out .vibio/experiments/seo-title-2026-01/result.json \
  --markdown-out

python vibio-memory/scripts/state_manager.py detectability \
  --project-root . \
  --experiment-plan .vibio/experiments/seo-title-2026-01/frozen/plan.json \
  --experiment-result .vibio/experiments/seo-title-2026-01/result.json \
  --out .vibio/experiments/seo-title-2026-01/detectability.json
```

工具只支持页面级 `randomized_page_holdout` 和 `matched_page_did`，会冻结输入 hash、逐页面基线摘要、seed、分组、主指标、护栏、窗口、MDE 和测量时区/来源契约，拒绝纯前后对比。实施前必须冻结 analysis timezone、时间粒度、source ID/kind/timezone、每个指标的唯一来源映射和 attribution model；分析 metadata 只能补充数据截止、finality/preliminary、分页、触限、采样、阈值和 data quality 等采集状态，不能新增来源或改写冻结字段。加载冻结计划时会从逐页基线重放 seed/design/treatment fraction 的分组与 balance，因此交换分组后重算 JSON hash 仍会被拒绝。分析阶段要求每个页面覆盖两个完整日窗口并重新绑定冻结基线，再计算页面级 DiD、近似置信区间并检查实现、污染、护栏、MDE 精度以及数据 finality、分页、触限、采样、阈值和归因元数据。输出分别遵循 `experiment.plan.schema.json` 和 `experiment.report.schema.json`。`eligible_incremental` 只表示具备人工增量解读资格，不判断效果方向，不自动等于 `incremental-positive`，也不证明排名、自然流量或收入因果。任何测量完整性门禁失败都会得到 `inconclusive`。`experiment.py` 不在正式报告中自动声称统计功效；独立的 `state_manager.py detectability` 会绑定冻结 MDE、alpha、正式报告及输入摘要，用报告的标准误确定性重算 power。只有 power >= 0.8 且置信区间包含 0 时，该证据才能支持 `no-detectable-change`；它不证明效果绝对为零，也不支持对未预注册指标的外推。

## 开发与验证

需要 Python 3.10 或更高版本。开发环境安装：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

修改 `SKILL.md` 或顶层 `references/` 后，按以下顺序运行硬闸门：

```bash
python scripts/build_skills.py --clean
python scripts/validate_repo.py --strict
pytest -q
python scripts/eval_runner.py --strict
git diff --check
```

机器可读 eval 报告：

```bash
python scripts/eval_runner.py --strict --json
```

使用自定义离线候选输出复测：

```bash
python scripts/eval_runner.py --strict --responses path/to/responses.json
```

`validate_repo.py` 检查仓库结构和测试定义，`eval_runner.py` 对手写 fixture 执行 typed assertions；二者不能互相替代。离线合同回归通过只说明规则、样例与评分器没有回归，不代表真实 Skill 触发、模型行为或 SEO 结果已被证明。只有在构建、严格校验、单元测试和合同回归全部通过后，生成目录才具备发布前的工程完整性；真实质量仍需同提示运行、人工/盲评和站点实验验证。

## 安装

先在仓库根目录执行构建和严格校验。然后把需要的 Skill 目录作为直接子目录安装到客户端的 skills 根目录。以 Codex 为例，个人目录通常是 `$CODEX_HOME/skills/`，未设置 `CODEX_HOME` 时是 `~/.codex/skills/`。

最小安装只需 `vibio/`，其 Skill 名称是 `vibio-seo`，且构建后包含完整参考包。推荐同时安装全部专项 Skill，以获得更准确的直接触发：

```bash
skills_root="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skills_root"
cp -R vibio vibio-plan vibio-audit vibio-fix vibio-keyword \
  vibio-content vibio-link vibio-review vibio-memory vibio-factory \
  "$skills_root/"
```

其他支持 `SKILL.md` 的客户端使用其对应 skills 根目录。不要只复制仓库顶层 `references/`；应安装构建完成、已自包含引用的各 Skill 目录。

## 使用

可以直接用中文描述业务目标，由 `vibio-seo` 选择模式并继续执行：

```text
审计这个站为什么产品页一直没有自然曝光，能修的直接修，之后告诉我怎么复测。

我们做德国工业采购市场。先用询盘、GSC 和可用的广告搜索词验证真实买家用语，再给出词族到页面映射。

上个月改了 canonical、产品页正文和内链。请读取 .vibio 变更记录，判断现在是有效、回退还是还太早。
```

也可以明确调用专项 Skill，例如 `vibio-keyword`、`vibio-content` 或 `vibio-link`。所有模式在开工前读取项目根 `.vibio/`，收工后只写回会影响后续决策的状态。

## Google 2026 基线纠错

以下规则用于阻止常见但无效或已经过时的“SEO 优化”：

| 误区 | v5 采用的规则 |
|---|---|
| Google AI Overviews / AI Mode 需要一套独立 GEO 技巧 | 它们建立在核心 Search 排名与质量系统之上；优先正常技术资格、原创价值、专业经验和用户体验 |
| `llms.txt` 能提升 Google 搜索或 AI 可见性 | Google Search 会忽略它；仅在目标平台明确记录支持时作为低优先级可选集成 |
| `Google-Extended` 控制内容是否出现在 Google Search 或 AI Overviews | 它不控制内容是否在 AI Overviews/AI Mode 中出现、被链接或用于 grounding，也不影响 Search 收录/排名；Google 同时将它列为限制相关模型训练用途的控制项 |
| FAQPage / HowTo 能带来 Google 富媒体搜索结果 | Google 已于 2026-05-07 停止 FAQ rich result，HowTo 也已退役；只有内容本身帮助用户时才保留 FAQ 或步骤，不为 SERP 收益添加标记 |
| title 必须 50-60 字符、description 必须 150-160 字符 | Google 没有这些固定限制；应准确、独特、与页面一致，并结合真实展示结果迭代 |
| Schema 能保证排名、富结果或生成式 AI 展示 | 结构化数据提供机器可读线索，并可使页面获得受支持搜索功能的资格；它不保证功能展示、排名或生成式 AI 展示 |
| Indexing API 可以提交普通页面 | Google Indexing API 只适用于受支持的 `JobPosting` 和直播 `BroadcastEvent` 页面 |
| GSC 查询可以和 GA4 用户转化确定性连接 | 两套系统只能按共享聚合维度结合；查询级收入只能是明确标注的估算 |
| GA4 仍原生提供 first-click、linear、position-based、time-decay 归因 | 这些模型已移除；实施前按 GA4 当前支持的模型和字段重新核验，不能沿用旧报表假设 |
| CPC、广告竞争或广告预算能代表自然排名能力 | 它们只提供付费市场和需求情报，不能替代 organic KD，也不能购买自然排名 |

易变规则以执行当天的 Google 官方文档为准，缓存参考资料仅用于导航。核心来源索引见 [references/google-search-docs.md](references/google-search-docs.md)、[references/geo-dominance.md](references/geo-dominance.md) 和 [references/paid-search-intelligence.md](references/paid-search-intelligence.md)。
