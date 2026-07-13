import type {
  ModeDefinition,
  ModeDraft,
  ModeDrafts,
  ProjectInput,
  ProjectProfile,
  ProviderDefinition,
  WorkspaceDraftV2,
} from "./types";

export const MODES: ModeDefinition[] = [
  {
    id: "plan",
    code: "01",
    label: "计划",
    title: "制定行动路线",
    description: "从业务结果、证据覆盖和团队产能出发，排出真正有依赖关系的下一段工作。",
    detailLabel: "现状、资源与限制",
    detailPlaceholder: "例如：团队每周可投入 2 个开发日和 1 篇专家内容；GSC 已接入，但 CRM 尚未按落地页归因……",
    evidenceHint: "推荐上传页面清单、GSC 导出、历史计划或业务说明。",
    output: "主导约束、Now / Next / Later、负责人、验证与停止条件",
    accent: "blue",
    task: {
      objective: {
        label: "这一阶段最想推进什么结果？",
        placeholder: "留空时使用项目的主要目标",
        rows: 3,
      },
      details: {
        label: "现有资源与限制",
        placeholder: "例如：GSC 已接入，开发每周可投入 2 天",
        rows: 4,
      },
      scope: {
        label: "计划范围",
        placeholder: "全站、某个市场或页面组",
      },
      timing: {
        label: "决策窗口",
        placeholder: "例如：本季度或接下来 6 周",
      },
    },
  },
  {
    id: "audit",
    code: "02",
    label: "审计",
    title: "定位搜索阻断",
    description: "先检查可访问、可渲染与可索引资格，再判断意图、价值、架构和业务路径。",
    detailLabel: "重点问题与页面范围",
    detailPlaceholder: "例如：德国站产品详情页近三个月几乎没有自然曝光；优先检查 /products/ 目录与对应模板……",
    evidenceHint: "可直接抓取公开 URL，或上传 HTML、DOM、robots、sitemap 与数据导出。",
    output: "观察证据、影响边界、置信度、优先级、修复和复验方式",
    accent: "cyan",
    task: {
      objective: {
        label: "这次最想确认什么？",
        placeholder: "留空时使用项目的主要目标",
        rows: 3,
      },
      details: {
        label: "已观察到的症状",
        placeholder: "例如：产品页近三个月几乎没有自然曝光",
        rows: 4,
      },
      scope: {
        label: "重点页面或目录",
        placeholder: "例如：/products/ 或某个页面模板",
      },
    },
  },
  {
    id: "fix",
    code: "03",
    label: "修复",
    title: "形成最小修复契约",
    description: "把已验证问题转成可审阅的代码或 CMS 修改方案，并明确产物验证和回滚条件。",
    detailLabel: "已验证问题与技术栈",
    detailPlaceholder: "粘贴审计发现、当前实现、框架/CMS、目标行为以及允许修改的范围。首版不会直接部署到生产。",
    evidenceHint: "推荐上传相关源码、模板、构建 HTML、审计报告或配置片段。",
    output: "修复契约、补丁/交接说明、验证清单、未验证项与回滚条件",
    accent: "orange",
    task: {
      objective: {
        label: "要修复的已确认问题",
        placeholder: "粘贴已验证的审计发现或目标行为",
        required: true,
        rows: 3,
      },
      details: {
        label: "当前实现与技术栈",
        placeholder: "框架/CMS、当前实现、期望行为与回滚要求",
        rows: 4,
      },
      scope: {
        label: "允许修改的范围",
        placeholder: "例如：仅产品详情页模板，不改 CMS 数据",
      },
    },
  },
  {
    id: "keyword",
    code: "04",
    label: "关键词",
    title: "验证真实买家需求",
    description: "用目标市场原生表达、SERP 意图与第一方数据，把查询族映射到正确页面。",
    detailLabel: "产品、买家任务与种子表达",
    detailPlaceholder: "说明产品/服务、目标买家是谁、他们要完成什么任务、已知询盘用语和现有落地页。不要机械翻译词表。",
    evidenceHint: "推荐上传匿名 RFQ 用语、GSC、广告搜索词、页面清单或竞品样本。",
    output: "查询族、验证状态、页面映射、蚕食风险与投资顺序",
    accent: "violet",
    task: {
      objective: {
        label: "要研究哪个产品或主题？",
        placeholder: "留空时使用项目的主要目标",
        rows: 3,
      },
      details: {
        label: "已知买家用语与任务",
        placeholder: "询盘用语、种子表达、采购场景或竞品样本",
        rows: 4,
      },
      scope: {
        label: "需要映射的页面",
        placeholder: "已有落地页、页面清单或待建页面类型",
      },
    },
  },
  {
    id: "write",
    code: "05",
    label: "内容",
    title: "产出可发布页面",
    description: "围绕已验证任务收集一手事实、建立证据账本，再写出有信息增益的目标市场内容。",
    detailLabel: "页面任务与品牌约束",
    detailPlaceholder: "说明页面类型、目标查询族、读者场景、必须回答的问题、CTA、品牌语气，以及不能声称的内容。",
    evidenceHint: "推荐上传专家访谈、产品资料、来源、现有页面与已验证关键词映射。",
    output: "目标语言成稿、metadata、证据账本、内链计划与对抗审查",
    accent: "green",
    task: {
      objective: {
        label: "要创建或改写什么页面？",
        placeholder: "页面类型、主题或目标查询",
        required: true,
        rows: 3,
      },
      details: {
        label: "事实、CTA 与品牌边界",
        placeholder: "必须回答的问题、可引用事实、品牌语气和不能声称的内容",
        rows: 4,
      },
      scope: {
        label: "目标查询与页面范围",
        placeholder: "查询族、现有 URL 或新页面位置",
      },
    },
  },
  {
    id: "link",
    code: "06",
    label: "链接",
    title: "改善发现与权威",
    description: "优先修复内部发现和商业路径，再用真实资产与关系形成可人工审核的外联机会。",
    detailLabel: "目标页面与链接问题",
    detailPlaceholder: "说明要支持的页面、已知孤儿页/深度问题、可用内容资产、合作关系或外链导出。",
    evidenceHint: "推荐上传页面库存、抓取链接表、外链导出与真实可推广资产说明。",
    output: "donor/目标页建议、机会池、编辑理由、风险与待人工审核草稿",
    accent: "gold",
    task: {
      objective: {
        label: "要支持哪个目标页面？",
        placeholder: "输入 URL、页面名称或页面组",
        required: true,
        rows: 3,
      },
      details: {
        label: "可用资产与真实关系",
        placeholder: "可推广内容、合作伙伴、已知孤儿页或外链导出",
        rows: 4,
      },
      scope: {
        label: "链接范围",
        placeholder: "内部发现、商业路径、外部权威或组合",
      },
    },
  },
  {
    id: "review",
    code: "07",
    label: "复盘",
    title: "判断改动是否有效",
    description: "先确认改动仍存在，再分层看抓取、可见性、站内行为与业务结果，避免把相关当因果。",
    detailLabel: "变更、日期与测量合同",
    detailPlaceholder: "说明改了什么、何时上线、影响页面、预期机制、主指标、护栏、比较窗口和同期干扰。",
    evidenceHint: "推荐上传 GSC/GA4/CRM 聚合导出、实验文件、上线产物或历史报告。",
    output: "七类判定、证据限制、保留/扩展/修订/回退决策与下一窗口",
    accent: "red",
    task: {
      objective: {
        label: "要复盘哪项已上线变更？",
        placeholder: "说明改了什么以及预期机制",
        required: true,
        rows: 3,
      },
      details: {
        label: "指标、护栏与同期干扰",
        placeholder: "主指标、护栏、可用数据与同期活动",
        rows: 4,
      },
      scope: {
        label: "受影响的页面",
        placeholder: "URL、目录、模板组或市场",
      },
      timing: {
        label: "上线日期与比较窗口",
        placeholder: "例如：2026-07-01 上线，按项目周期比较",
      },
    },
  },
  {
    id: "recover",
    code: "08",
    label: "恢复",
    title: "诊断流量或索引下滑",
    description: "先验证异常是否真实，再检查技术回归、安全、意图、竞争、季节性与更新线索。",
    detailLabel: "异常窗口与同期变化",
    detailPlaceholder: "说明何时开始下滑、影响哪些目录/市场/设备，以及同期部署、迁移、内容、人工处置或安全事件。",
    evidenceHint: "推荐上传同口径前后窗口、变更记录、受影响 URL、GSC 与部署历史。",
    output: "异常范围、原因树、证据强度、可逆动作与观察/停止条件",
    accent: "slate",
    task: {
      objective: {
        label: "发生了什么下降或索引异常？",
        placeholder: "描述可观察的流量、曝光、排名或索引变化",
        required: true,
        rows: 3,
      },
      details: {
        label: "同期变更与事件",
        placeholder: "部署、迁移、内容调整、安全事件或人工处置",
        rows: 4,
      },
      scope: {
        label: "受影响范围",
        placeholder: "目录、市场、设备、查询类型或 URL 组",
      },
      timing: {
        label: "异常开始时间",
        placeholder: "准确日期或大约时间窗口",
      },
    },
  },
];

export const FALLBACK_PROVIDERS: ProviderDefinition[] = [
  {
    id: "deepseek",
    label: "DeepSeek",
    description: "DeepSeek V4，支持长上下文与思考模式",
    default_model: "deepseek-v4-flash",
    models: [
      { id: "deepseek-v4-flash", label: "DeepSeek V4 Flash" },
      { id: "deepseek-v4-pro", label: "DeepSeek V4 Pro" },
    ],
  },
  {
    id: "mimo",
    label: "MiMo",
    description: "小米开放平台的 OpenAI-compatible 模型",
    default_model: "mimo-v2-flash",
    models: [{ id: "mimo-v2-flash", label: "MiMo V2 Flash" }],
  },
  {
    id: "openai",
    label: "OpenAI",
    description: "OpenAI 通用与推理模型",
    default_model: "gpt-4.1-mini",
    models: [
      { id: "gpt-4.1-mini", label: "GPT-4.1 mini" },
      { id: "gpt-4.1", label: "GPT-4.1" },
    ],
  },
  {
    id: "qwen",
    label: "通义千问",
    description: "阿里云百炼兼容接口",
    default_model: "qwen-plus",
    models: [{ id: "qwen-plus", label: "Qwen Plus" }],
  },
  {
    id: "moonshot",
    label: "Kimi",
    description: "Moonshot 长上下文模型",
    default_model: "kimi-k2.5",
    models: [{ id: "kimi-k2.5", label: "Kimi K2.5" }],
  },
  {
    id: "zhipu",
    label: "智谱 GLM",
    description: "智谱开放平台兼容接口",
    default_model: "glm-4.5",
    models: [{ id: "glm-4.5", label: "GLM-4.5" }],
  },
  {
    id: "siliconflow",
    label: "SiliconFlow",
    description: "可选择平台支持的模型 ID",
    default_model: "deepseek-ai/DeepSeek-V3.2",
    models: [{ id: "deepseek-ai/DeepSeek-V3.2", label: "DeepSeek V3.2" }],
  },
];

export const EMPTY_PROJECT_PROFILE: ProjectProfile = {
  projectName: "",
  siteUrl: "",
  market: "",
  language: "",
  conversion: "",
  primaryGoal: "",
  audience: "",
  businessModel: "",
  capacity: "",
  allowNetworkEvidence: true,
  allowStateDraft: true,
};

export const EMPTY_MODE_DRAFT: ModeDraft = {
  objective: "",
  details: "",
  scope: "",
  timing: "",
};

export const EMPTY_MODE_DRAFTS: ModeDrafts = {
  plan: { ...EMPTY_MODE_DRAFT },
  audit: { ...EMPTY_MODE_DRAFT },
  fix: { ...EMPTY_MODE_DRAFT },
  keyword: { ...EMPTY_MODE_DRAFT },
  write: { ...EMPTY_MODE_DRAFT },
  link: { ...EMPTY_MODE_DRAFT },
  review: { ...EMPTY_MODE_DRAFT },
  recover: { ...EMPTY_MODE_DRAFT },
};

export const EMPTY_WORKSPACE_DRAFT: WorkspaceDraftV2 = {
  schemaVersion: 2,
  profile: { ...EMPTY_PROJECT_PROFILE },
  modes: EMPTY_MODE_DRAFTS,
  sharedContext: "",
};

export const EMPTY_PROJECT: ProjectInput = {
  ...EMPTY_PROJECT_PROFILE,
  objective: "",
  scope: "",
  details: "",
  decisionWindow: "",
};

export const ACCEPTED_EVIDENCE = ".csv,.json,.html,.htm,.md,.txt,.xml";
export const MAX_EVIDENCE_FILES = 6;
export const MAX_EVIDENCE_BYTES = 90 * 1024;
export const MAX_EVIDENCE_TOTAL_BYTES = 90 * 1024;
