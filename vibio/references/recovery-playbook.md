# Recovery Playbook — 流量、收录与排名异常恢复

恢复工作的第一原则是先确认数据、范围和机制，再选择动作。固定跌幅、等待周数或“恢复周期”无法适用于所有站点，也不能把与 Google 更新日期重合直接当作因果。

## 一、确认异常真实存在

1. 检查 GSC/GA4/CRM/排名工具是否延迟、漏数、过滤变化或埋点中断；
2. 对齐国家、设备、搜索类型、品牌/非品牌、页面组和可比日期；
3. 用该站历史波动、季节性和可比 cohort 判断变化是否异常；
4. 区分 clicks、impressions、CTR、position、索引、自然会话和业务转化；
5. 记录开始时间、影响范围、数据来源与置信度。

业务关键页大规模不可访问、误 noindex、严重状态错误、安全事件或 GSC manual action 可立即按 Critical 处理。其他变化按影响与证据排序，不设通用跌幅阈值。

## 二、定位范围

```text
异常
├─ 全站 / 模板 / 目录 / 单页？
├─ 所有国家设备，还是特定市场？
├─ 品牌、非品牌或某个查询族？
├─ 收录/抓取、曝光、点击，还是转化？
└─ 是否与部署、迁移、内容批次、需求季节或 SERP 变化同窗？
```

查看 `.vibio/changelog.md`、部署记录、Search Status Dashboard、manual action/安全问题和竞品/SERP 样本。时间重合是调查线索，不是根因结论。

## 三、按机制恢复

### 技术/部署回归

- 比较保存基线与当前状态码、robots、canonical、渲染、hreflang、sitemap、内链和分析标记；
- 定位到具体模板/发布，优先回滚可逆的破坏性改动或做最小修复；
- 在真实渲染产物和关键 URL 上验证；
- 用 GSC URL Inspection / sitemap / 正常发现路径观察，不宣称“提交 URL 会加速或保证恢复”。

### Manual action / 安全问题

- 以 GSC 通知的具体问题为准；
- 全面清除违规/被黑内容，保留证据和受影响范围；
- 符合条件时提交 reconsideration request；
- 不承诺审核或恢复时间。

### 内容、意图或产品错配

- 比较掉量查询、目标地区当前 SERP、页型和页面承诺；
- 检查事实过时、信息增益消失、产品不可用、重复/自相蚕食或用户任务改变；
- 选择刷新、重构、合并、重定向、保留历史日期或停止，不为“新鲜度”机械改发布日期；
- 只有正文实质更新且日期对用户有意义时才更新可见日期/`dateModified`。

### 竞争或 SERP 形态变化

- 验证竞品是否真的改善产品、证据、页面体验、资产或分发；
- 检查 AI Overviews、购物、地图、视频等是否改变点击路径；
- 判断该机会是否仍有商业价值，再决定改页、建资产、调整渠道预期或停止争夺；
- 不默认“match or exceed”，也不套固定 SERP 功能 CTR 折扣。

### 需求、季节或品牌变化

- 用 Trends、GSC、Ads search terms、销售/CRM 和市场事件交叉判断；
- 区分行业需求下降、品牌需求下降、库存/价格/地区限制和搜索迁移；
- SEO 无法修复产品无货、市场萎缩或错误商业定位，应把动作交给对应负责人。

### Google 更新相关

- 查 Search Status Dashboard 与官方说明；
- 不基于行业传言猜“更新针对什么”；
- 按受影响页面的具体用户价值、垃圾政策、产品评论/站点声誉等相关官方文档审查；
- 做对用户和业务有实质价值的修复，不做为了“讨好更新”的批量微调；
- Google 的 helpful content system 已并入核心排名系统，不把它当独立更新标签或单一处罚机制。

## 四、验证恢复

使用 `references/review-engine.md`：

- 先确认修复实施且没有回归；
- 再确认 Google 有机会抓取/索引；
- 比较受影响 cohort、查询/国家/设备与可比对照；
- 最后看合格自然访问、线索和业务结果；
- 结论使用 `not-yet-observable / directional-positive / incremental-positive / no-detectable-change / negative-or-regression / inconclusive`。

观察窗口由该站抓取历史、数据量、季节和业务周期决定。不在任意固定稳定期内禁止所有改动；但应避免同时堆叠无法解释的多项变化。

## 五、记录格式

```markdown
## RECOVERY — YYYY-MM-DD
- Incident window / scope:
- Data validation:
- Affected markets/pages/queries:
- Suspected mechanisms and evidence:
- Confounders:
- Action / owner / rollback plan:
- Implementation verification:
- Leading and business indicators:
- Verdict / next check:
```

只把会改变未来决策、且证据足够的经验匿名写入跨项目 learnings。单次相关变化不能升级为普遍恢复时限或阈值。

## 六、预防

- 部署前后自动检查状态、robots、canonical、hreflang、结构化数据和关键内容；
- 重大迁移保存 URL 映射、渲染基线和回滚路径；
- 保持 append-only changelog 与页面/查询 cohort；
- 监控业务关键页的可访问性、索引与转化测量；
- 根据内容风险和真实衰退信号安排复核，不机械“季度刷新”。

## 七、不要做

- 不用固定跌幅判断原因或严重度。
- 不把更新/部署时间重合当因果。
- 不承诺恢复时间、排名或流量幅度。
- 不为新鲜度只改日期，也不把普通页面“重新提交”当恢复策略。
- 不在未验证实施、数据和范围前批量改内容/链接。
- 不把 GSC 与 GA4 差异直接当测量故障，也不确定性连接查询到转化。
