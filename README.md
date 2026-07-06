# Vibio SEO v4 — 统一搜索优化操作系统

Vibio 的端到端搜索优化技能。不是用来"解释 SEO 是什么"的——它是一个完整的 SEO/GEO 操作系统：诊断瓶颈、自动识别技术栈、多栈修复、**关键词目标市场验证（五道闸门确保目标国家真实买家确实在搜）**、逆向 SERP 写作、5-Agent 盲审、**内链系统工程（发布回填协议/孤儿页救援/权重导流）**、**外链分级获取（链接资产/行业目录/数字 PR/品牌提及）**、闭环复盘、权威阶梯、预测排名、竞品战争、算法恢复、内容修剪、归因 ROI。同一个质量信号同时服务于传统搜索排名和 AI 搜索引用（Google AI Overviews / ChatGPT / Perplexity）。

## v3 进化（历史，v1 → v3）

| 维度 | v1 | v3 |
|------|-----|-----|
| 工作模式 | 3 | 7 (PLAN/AUDIT/FIX/WRITE/KEYWORD/REVIEW/RECOVER) |
| 修复栈 | Next.js 仅 | 5 栈 (Next.js/WordPress/Shopify/Static/URL-only) |
| Reference 文件 | 5 个 / 760 行 | 36 个 / 4,433 行 |
| 项目记忆 | 无 | .vibio/ 持久化，跨会话连续 |
| 审查基准 | 民间 best practice | Google 官方文档，每条发现带规范 URL |
| 内容质量 | 基础流水线 | 竞品拆解 → 证据表 → AI 优先写作 → 5-Agent 盲审 95 分闸门 |
| SEO/GEO 统一 | 分离 | 一次优化，全域制胜 |
| 闭环复盘 | 无 | 改动 → 等重抓窗口 → 阈值判定 → 决策 → 写回 |
| 预测能力 | 无 | 排名概率/流量预估/时间线/收入预测 + 预测兑现调和 |
| 竞品监控 | 无 | 竞品战争室 + AI 可见性情报 |
| 算法恢复 | 无 | 5 原因诊断 + 分因恢复手册 |
| ROI 归因 | 无 | B2B 队列归因含 18 个月滞后调整 |
| 权威阶梯 | 无 | KD 分级关键词排序战略 |
| 内容修剪 | 无 | 季度库存评分 + 合并/删除决策矩阵 |
| PAA 缺口 | 无 | SERP 问题级缝隙提取，直入 WRITE 管线 |
| 语义网络 | 无 | 实体节点 + 用户旅程 + 格式矩阵 + 内链拓扑 |
| GEO 体系 | 无 | 统一审计/内容模板/竞品情报/平台策略 |
| SEO 实验 | 无 | A/B 测试框架含统计显著性 |

## 八种工作模式

- **PLAN** — 90 天路线图、权威阶梯架构、周/月节奏
- **AUDIT** — 全站审查 + 统一搜索审计（传统 + AI 可见性）→ 0-100 评分
- **FIX** — 5 栈修复（代码编辑 / CMS 配置 / 可粘贴片段）
- **WRITE** — 关键词验证 → SERP 逆向 → PAA 缺口 → 证据表 → AI 优先写作 → 5-Agent 盲审 95 分闸门 → 内链回填交付
- **KEYWORD** — 买家真实语料 → 真实数据 → 意图 → **目标市场验证五道闸门（防直译陷阱）** → 级联阶段 → 页面映射 → 簇
- **LINK** 🆕 — 内链审计/发布回填/孤儿页救援/Donor-Acceptor 权重导流 + 外链启动闸门/链接资产/分级战术/品牌提及 AI 引用 KPI
- **REVIEW** — 读改动历史 → 重抓窗口 → 定量阈值判定 → 预测调和 → 决策
- **RECOVER** — 流量下降 → 5 原因诊断 → 分因恢复 → 监控

## v4 进化（相对 v3）

| 维度 | v3 | v4 |
|------|-----|-----|
| 工作模式 | 7 | 8（新增 LINK 内外链引擎） |
| 关键词选择 | 数据 + 意图 + 可操作性 | + 目标市场验证五道闸门：母语性证据 / SERP 试金石 / 分国家量 / 搜索者身份排除 / 商业路径；零搜索量 B2B 词判定框架；买家用语挖掘工具箱（询盘原文/GSC/母语竞品/Autocomplete/Reddit/B2B 平台） |
| 内链 | 散落各文件的一次性建议 | 统一操作手册：三层拓扑、锚库轮换、发布日回填协议（不发孤儿页）、Donor-Acceptor 季度导流、审计六检测项、links tracker |
| 外链 | 一张空 tracker | 完整获取系统：启动闸门、链接资产先行、三级战术（工业目录/提及回收/竞品差距/数字 PR/专家引用平台）、真实转化率预期、锚分布与速率安全、disavow 现代定位 |
| AI 引用信号 | 内容侧 GEO | + 链接侧 GEO：品牌提及（含无链）按 ~3x 于反向链接的 AI 引用相关性纳入 KPI；fan-out 意图簇选词 |
| 内容装配 | title/meta 基础规则 | + 防重写细则（圆括号>方括号、长度阈值）、作者实体 schema、原创影像优先、季度刷新预排 |

## 文件结构

```text
vibio_seo/
├── vibio/SKILL.md                        # 主入口：8 模式 + 15 条核心规则（含 SEO/GEO 统一原则）
├── vibio-plan/ vibio-audit/ vibio-fix/   # 专项子 skill（各自含 SKILL.md + references 副本 + evals）
├── vibio-keyword/ vibio-content/
├── vibio-link/ 🆕 vibio-review/
├── vibio-memory/ vibio-factory/
├── README.md
└── references/                           # 39 文件 / 5,000+ 行
    ├── operating-system.md               # PLAN 引擎 + GEO 追踪 + 阈值 + 预测调和
    ├── skill-arsenal.md                  # 27 专家工具地图
    ├── delivery-template.md              # PLAN 交付结构
    │
    ├── seo-fix-principles.md             # 12+1 维度修复目标规格（含 AI 搜索就绪度）
    ├── stack-detection.md                # 8 种栈自动检测
    ├── google-search-docs.md             # Google 官方文档审查基准
    ├── stack-adapters/                   # 5 栈修复配方
    │   ├── nextjs.md
    │   ├── wordpress.md
    │   ├── shopify.md
    │   ├── static-astro.md
    │   └── url-only.md
    │
    ├── write-playbook.md                 # 11 阶段文章生产管线 + 5-Agent 盲审闸门
    ├── competitor-teardown.md            # 竞品拆解 + 覆盖 vs 缺口矩阵
    ├── sourcing-and-eeat.md              # 证据表 + EEAT 配方 + AI 可摘引 + 去 AI 规则 + 盲审计分依据
    ├── adversarial-review.md             # 5 Agent 独立盲审，95 分闸门，5 轮迭代上限
    ├── geo-content-patterns.md           # 7 种 AI 优先内容模板 + 跨平台差异速查
    │
    ├── geo-dominance.md                  # 统一 AI 搜索策略：llms.txt / 实体信号 / 平台差异
    ├── geo-audit.md                      # 5 阶段 0-100 分统一搜索审计
    ├── geo-competitive-intel.md          # GEO 竞品情报 + 攻击手册
    │
    ├── authority-cascade.md              # 🆕 权威阶梯：KD 分级排序战略
    ├── semantic-networks.md              # 🆕 语义内容网络：超越 topic cluster
    ├── content-pruning.md                # 🆕 内容修剪：季度库存评分 + 删除/合并决策
    ├── paa-gap-analysis.md               # 🆕 PAA 缺口：SERP 问题级缝隙提取
    │
    ├── predictive-seo.md                 # 排名/流量/时间/收入预测 + 调和闭环
    ├── competitive-war-room.md           # 竞品战争室（含 AI 可见性维度）
    ├── recovery-playbook.md              # 算法恢复手册
    ├── roi-attribution.md                # SEO→收入管道 + B2B 队列归因
    ├── serp-feature-targeting.md         # SERP 特征攻占
    ├── entity-strategy.md                # 知识图谱 + 主题权威
    ├── migration-playbook.md             # 域名/平台迁移
    ├── content-decay.md                  # 内容衰减检测 + 刷新阶梯
    ├── multi-language-ops.md             # 多语言运营
    ├── seo-experimentation.md            # A/B 测试 + 统计显著性
    │
    ├── keyword-validation.md             # 🆕 v4 目标市场关键词验证：五道闸门 + 买家用语挖掘 + 零量词判定
    ├── link-architecture.md              # 🆕 v4 内链系统工程：拓扑/锚库/回填协议/审计/权重导流
    ├── backlink-playbook.md              # 🆕 v4 外链获取：启动闸门/链接资产/分级战术/outreach/安全
    │
    ├── state-templates.md                # .vibio/ 项目记忆模板（v4：+验证列/级联列/links tracker）
    ├── keyword-engine.md                 # KEYWORD 引擎（v4：+验证闸门）
    └── review-engine.md                  # REVIEW 引擎（含定量阈值）
```

## 设计原则

- SEO 和 AI 搜索是同一个问题——一次优化，全域制胜
- 先读 `.vibio/` 项目记忆，再干活；收工写回，不重启
- 自动检测技术栈，不假设 Next.js
- 先找主瓶颈，再排优先级
- 默认动手修，改完在渲染产物里验证
- 审查引用 Google 官方文档 URL
- 能路由到 27 个专家工具就不手搓
- **关键词不过目标市场验证不建页**——直译假词是最贵的选词错误
- 内容不达 95 分盲审闸门不交付
- **不发布孤儿页**——发布日回填 2-3 条入链是交付的一部分
- 外链先过启动闸门（有资产才 outreach），品牌提及按 AI 引用 KPI 追踪
- 预测必须调和——每月对比预测值和实际值
- SERP 改动等 2-6 周重抓窗口再判见效
- 不承诺排名、不承诺快速见效

## 安装

把本目录复制到 `~/.claude/skills/vibio_seo`，重启 Claude Code 生效。
