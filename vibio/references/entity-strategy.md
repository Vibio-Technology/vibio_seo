# 实体与品牌可核验性策略

实体策略帮助搜索者和平台确认“这家公司/产品是谁、提供什么、与哪些真实组织和产品有关”。它不承诺进入 Knowledge Graph、获得 Knowledge Panel 或提高 AI 引用。

## 一、建立实体事实表

只记录可证实信息：

```text
Legal name / trading brand / alternate names:
Official website and canonical homepage:
Products/services and supported markets:
Physical/service locations and contact channels:
Founders/leaders/experts when publicly relevant:
Certifications, memberships and issuing bodies:
Official profiles, marketplace listings and partners:
Source / owner / verified_on / public boundary:
```

区分法定名称、品牌名和产品名；不同场景可使用适合用户的名称，不要求 title、H1、正文和所有档案机械重复完整法定名。

## 二、修复一致性与可验证性

- 官网 About/Contact/政策页准确说明主体、地址、联系方式、市场和责任；
- 官方社交、GBP、协会、认证、市场平台等资料保持真实、有人维护；
- 产品、认证、奖项和合作关系链接到发布主体或原始证据；
- 过期地址、旧品牌、合并实体和经销商关系要明确处理；
- 不制造评论、伙伴、媒体、资历或第三方提及。

一致性不等于每个平台一字不差。法定字段一致，面向用户的短品牌和本地化描述可以不同。

## 三、结构化数据

在适合的首页/About/组织页面，根据当前 Google 文档和可见内容使用 Organization；网站名称相关标记按当前 Site names 文档处理。只填写真实、可维护属性：

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Verified organization name",
  "alternateName": "Verified brand name",
  "url": "https://www.example.com/",
  "logo": "https://www.example.com/logo.png",
  "sameAs": ["https://www.linkedin.com/company/verified-profile"]
}
```

- `sameAs` 只指向同一主体的真实官方/权威页面；不是“越多越好”；
- 地址、联系、foundingDate 等只有可核验且适合公开时填写；
- 不全站重复注入冲突的 Organization graph；
- 结构化数据提供相应功能资格，不保证 Knowledge Panel、站点名、排名或 AI 引用。

执行前核验：https://developers.google.com/search/docs/appearance/structured-data/organization

## 四、Wikipedia 与 Wikidata

- Wikipedia 需要独立可靠来源与社区 notability，不能为 SEO 自建宣传条目、雇人隐瞒利益关系或制造来源；
- Wikidata 条目也必须符合其规则和可核验来源，不是没有 Wikipedia 时的“捷径”；
- 只有真实存在、准确且确属同一实体时，才作为 `sameAs` 候选；
- 没有 Wikipedia/Wikidata 不构成 SEO 错误，也不能据此判定品牌不权威。

## 五、实体内容与任务网络

围绕真实产品、属性、应用、标准、案例和支持任务组织页面。每个页面完成一个明确任务并提供独有证据；不为“覆盖所有实体关系”批量建薄页。

使用 `semantic-networks.md` 做查询族/页面/内链映射，使用 `keyword-validation.md` 验证市场需求。产品关系、兼容和认证不得因语义关联而虚构。

## 六、第三方佐证

优先真实业务关系：认证机构、协会、客户/伙伴、展会、媒体、研究、市场平台和评论。每项记录资格、上下文、链接/引荐和业务结果。

不把提及数、Wikipedia、sameAs 或目录数量压成“实体权威分”。品牌提及可以支持 PR 和需求观察，但不能固定换算为排名或 AI 信号。

## 七、测量

- GSC 品牌/产品查询趋势，注意查询匿名化；
- 品牌 SERP 的名称、官方页面和错误信息人工样本；
- GBP/目录/伙伴的引荐和合格业务结果；
- 结构化数据语法与对应搜索功能状态；
- 带日期、市场的平台引用观察（仅方向性）。

知识面板是否出现由 Google 决定。若信息错误，按平台官方反馈流程修正；不要承诺创建或控制面板。

## 八、不要做

- 不将“实体/主题权威”描述成公开可测的 Google 分数。
- 不为 SEO 制造 Wikipedia/Wikidata、媒体、评论、认证或伙伴关系。
- 不把 Organization/WebSite Schema 称为 essential 排名因素。
- 不要求所有页面、title 和 H1 重复完整法定名称。
- 不把 sameAs、提及数或实体覆盖换算成 Knowledge Panel/AI 引用保证。
