import type {
  EvidenceFile,
  ModeId,
  ProjectInput,
  WorkflowArtifactKind,
  WorkflowContext,
  WorkflowStep,
  WorkflowStepStatus,
} from "./types";

export const WORKFLOW_MODE_ORDER = [
  "audit",
  "recover",
  "keyword",
  "plan",
  "fix",
  "write",
  "link",
  "review",
] as const satisfies readonly ModeId[];

export const MAX_WORKFLOW_CONTEXT_REPORTS = 3;
export const MAX_WORKFLOW_REPORT_JSON_BYTES = 48 * 1024;

const RECOVERY_WAITING_REASON = "未发现明确的流量下滑、搜索表现骤降或索引异常信号。";
const REVIEW_WAITING_REASON =
  "等待已上线变更，或 GSC、GA4、CRM、实验类可比测量证据后再复盘。";

const WORKFLOW_ARTIFACTS: Record<ModeId, WorkflowArtifactKind> = {
  plan: "execution_plan",
  audit: "audit_findings",
  fix: "fix_contract",
  keyword: "query_map",
  write: "publish_package",
  link: "link_plan",
  review: "review_decision",
  recover: "incident_assessment",
};

const MODE_CONTEXT_INPUTS: Record<ModeId, readonly ModeId[]> = {
  recover: [],
  audit: ["recover", "plan"],
  keyword: ["audit", "recover", "plan"],
  plan: ["recover", "audit", "keyword"],
  fix: ["recover", "audit", "plan"],
  write: ["keyword", "plan", "fix"],
  link: ["audit", "plan", "write"],
  review: ["plan", "fix", "write", "link"],
};

const RECOVERY_PATTERNS = [
  /(?:自然搜索|搜索|organic\s+)?(?:流量|点击|曝光|排名|收录|索引).{0,12}(?:下滑|下降|骤降|暴跌|锐减|减少|丢失|消失|掉出|异常)/i,
  /(?:下滑|下降|骤降|暴跌|锐减|丢失|异常).{0,12}(?:自然搜索|搜索|流量|点击|曝光|排名|收录|索引)/i,
  /(?:索引|收录)(?:覆盖)?(?:异常|故障|问题)/i,
  /\b(?:organic\s+)?(?:traffic|clicks?|impressions?|rankings?|indexed pages?).{0,24}(?:drop|declin|fall|loss|decreas|plummet|anomal)/i,
  /\b(?:deindex(?:ed|ing)?|indexing (?:issue|problem|anomaly)|index coverage issue)\b/i,
];

const RECOVERY_NEGATIONS = [
  /(?:没有|并无|未发现|未出现|不存在|无)(?:明显|明确|任何)?(?:的)?\s*(?:(?:自然搜索|搜索|站点|网站|页面|gsc)\s*)?(?:流量|点击|曝光|排名|收录|索引).{0,8}(?:下滑|下降|骤降|暴跌|锐减|减少|丢失|消失|掉出|异常)/gi,
  /\b(?:no|without)\s+(?:organic\s+)?(?:traffic|clicks?|impressions?|rankings?|indexing).{0,16}(?:drop|declin|loss|issue|problem|anomaly)\b/gi,
];

const RECOVERY_HYPOTHETICALS = [
  /(?:防止|避免|预防|防范|降低).{0,24}(?:自然搜索|搜索|流量|点击|曝光|排名|收录|索引).{0,16}(?:下滑|下降|骤降|减少|丢失|异常)/gi,
  /(?:下滑|下降|骤降|减少|丢失|异常).{0,6}(?:风险|可能|预警|预防)/gi,
  /\b(?:prevent|avoid|mitigat\w*|reduce the risk of).{0,36}(?:traffic|clicks?|impressions?|rankings?|indexing).{0,20}(?:drop|declin|loss|issue|anomal)/gi,
  /(?:如果|假如|一旦|万一|是否|假设).{0,48}(?:自然搜索|搜索|流量|点击|曝光|排名|收录|索引).{0,20}(?:下滑|下降|骤降|减少|丢失|异常)/gi,
  /\b(?:if|whether|suppose|assuming).{0,64}(?:traffic|clicks?|impressions?|rankings?|indexing).{0,24}(?:drop|declin|loss|issue|anomal)/gi,
];

const RECOVERY_OBSERVED_PATTERNS = [
  /(?:已|已经|当前|目前|最近|近期|过去|今年|去年|上月|本月|本周|开始|出现|发生|突然|骤然|以来|下降了|减少了|丢失了)/i,
  /(?:骤降|暴跌|锐减|消失|掉出)/i,
  /\b(?:has|have|had|currently|recently|since|started|began|observed|dropped|declined|fell|lost|last (?:week|month|quarter|year))\b/i,
];

const DEPLOYED_CHANGE_PATTERNS = [
  /(?:已|已经|刚刚|已完成).{0,24}(?:上线|发布|部署|改版|修复|迁移|变更)/i,
  /(?:上线|发布|部署|改版|修复|迁移|变更).{0,16}(?:已完成|已结束|完成于)/i,
  /\b(?:deployed|released|launched|rolled out|went live)\b/i,
];

const REVIEW_FILE_PATTERNS = [
  /(?:^|[._\-/\s])(?:gsc|ga4|crm)(?:[._\-/\s]|$)/i,
  /(?:search[ _-]?console|google[ _-]?analytics|experiment|holdout|a[ _-]?b[ _-]?test|实验|对照组)/i,
];

const REVIEW_DATA_PATTERNS = [
  /(?:gsc|search console).{0,32}(?:clicks?|impressions?|ctr|position|点击|曝光|排名|导出|数据)/i,
  /(?:ga4|google analytics).{0,32}(?:sessions?|users?|conversions?|会话|用户|转化|导出|数据)/i,
  /(?:crm).{0,32}(?:leads?|opportunities|revenue|线索|商机|收入|询盘|导出|数据)/i,
  /(?:实验|experiment|holdout|a\/b test).{0,32}(?:结果|报告|数据|窗口|样本|result|report|data|window|sample)/i,
];

const REVIEW_AVAILABILITY_PATTERNS = [
  /(?:已有|已提供|已上传|已导出|已附上|数据可用|包含数据)/i,
  /\b(?:available|provided|attached|uploaded|exported|included)\b/i,
];

const MODE_LABELS: Record<ModeId, string> = {
  audit: "审计",
  recover: "恢复",
  keyword: "关键词",
  plan: "计划",
  fix: "修复",
  write: "内容",
  link: "链接",
  review: "复盘",
};

const STATUS_LABELS: Record<WorkflowStepStatus, string> = {
  pending: "待运行",
  running: "运行中",
  complete: "已完成",
  waiting: "等待材料",
  skipped: "已跳过",
  error: "失败",
};

function projectText(project: ProjectInput): string {
  return Object.values(project)
    .filter((value): value is string => typeof value === "string")
    .join("\n");
}

function evidenceSignalText(evidence: readonly EvidenceFile[]): string {
  return evidence
    .filter((file) => file.size > 0 && file.content.trim().length > 0)
    .map((file) => `${file.name}\n${file.type}\n${file.content}`)
    .join("\n");
}

function matchesAny(value: string, patterns: readonly RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(value));
}

function hasRecoverySignal(value: string): boolean {
  const withoutNegatedSignals = [...RECOVERY_NEGATIONS, ...RECOVERY_HYPOTHETICALS].reduce(
    (current, pattern) => current.replace(pattern, ""),
    value,
  );
  return (
    matchesAny(withoutNegatedSignals, RECOVERY_PATTERNS) &&
    matchesAny(withoutNegatedSignals, RECOVERY_OBSERVED_PATTERNS)
  );
}

function hasReviewSignal(project: ProjectInput, evidence: readonly EvidenceFile[]): boolean {
  const projectValue = projectText(project);
  const evidenceValue = evidence.map((file) => file.content).join("\n");
  const combined = `${projectValue}\n${evidenceValue}`;

  if (matchesAny(combined, DEPLOYED_CHANGE_PATTERNS)) return true;
  if (
    matchesAny(projectValue, REVIEW_DATA_PATTERNS) &&
    matchesAny(projectValue, REVIEW_AVAILABILITY_PATTERNS)
  ) return true;
  if (matchesAny(evidenceValue, REVIEW_DATA_PATTERNS)) return true;

  return evidence.some((file) =>
    file.size > 0 &&
    file.content.trim().length > 0 &&
    matchesAny(`${file.name}\n${file.type}`, REVIEW_FILE_PATTERNS),
  );
}

function jsonStringBytes(value: string): number {
  return new TextEncoder().encode(JSON.stringify(value)).byteLength;
}

function truncateReportForContext(value: string): { report: string; truncated: boolean } {
  if (jsonStringBytes(value) <= MAX_WORKFLOW_REPORT_JSON_BYTES) {
    return { report: value, truncated: false };
  }

  let low = 0;
  let high = value.length;
  while (low < high) {
    const middle = Math.ceil((low + high) / 2);
    if (jsonStringBytes(value.slice(0, middle)) <= MAX_WORKFLOW_REPORT_JSON_BYTES) {
      low = middle;
    } else {
      high = middle - 1;
    }
  }

  let report = value.slice(0, low);
  if (/[\uD800-\uDBFF]$/.test(report)) report = report.slice(0, -1);
  return { report, truncated: true };
}

export function buildWorkflowPlan(
  project: ProjectInput,
  evidence: readonly EvidenceFile[] = [],
  reviewProject: ProjectInput = project,
): WorkflowStep[] {
  const recoveryReady = hasRecoverySignal(`${projectText(project)}\n${evidenceSignalText(evidence)}`);
  const reviewReady = hasReviewSignal(reviewProject, evidence);

  return WORKFLOW_MODE_ORDER.map((mode) => {
    if (mode === "recover" && !recoveryReady) {
      return { mode, status: "skipped", reason: RECOVERY_WAITING_REASON };
    }
    if (mode === "review" && !reviewReady) {
      return { mode, status: "waiting", reason: REVIEW_WAITING_REASON };
    }
    return { mode, status: "pending" };
  });
}

export function buildWorkflowContext(steps: readonly WorkflowStep[]): WorkflowContext {
  const completedReports = steps
    .filter(
      (step): step is WorkflowStep & { report: string } =>
        step.status === "complete" && typeof step.report === "string" && step.report.trim().length > 0,
    )
    .slice(-MAX_WORKFLOW_CONTEXT_REPORTS)
    .map((step) => {
      const report = step.report.trim();
      const bounded = truncateReportForContext(report);
      return {
        mode: step.mode,
        artifactKind: WORKFLOW_ARTIFACTS[step.mode],
        report: bounded.report,
        truncated: bounded.truncated,
        ...(step.createdAt ? { createdAt: step.createdAt } : {}),
      };
    });

  return {
    schemaVersion: "vibio-web.workflow-context.v1",
    completedReports,
  };
}

export function buildWorkflowContextForMode(
  steps: readonly WorkflowStep[],
  targetMode: ModeId,
): WorkflowContext {
  const preferredModes = new Set(MODE_CONTEXT_INPUTS[targetMode]);
  let relevant = steps.filter(
    (step) => step.status === "complete" && preferredModes.has(step.mode),
  );
  if (targetMode === "review" && relevant.length > MAX_WORKFLOW_CONTEXT_REPORTS) {
    const plan = relevant.find((step) => step.mode === "plan");
    if (plan) {
      relevant = [
        plan,
        ...relevant.filter((step) => step !== plan).slice(-(MAX_WORKFLOW_CONTEXT_REPORTS - 1)),
      ];
    }
  }
  return buildWorkflowContext(relevant);
}

function inline(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function aggregateWorkflowMarkdown(
  project: ProjectInput,
  steps: readonly WorkflowStep[],
): string {
  const counts = Object.fromEntries(
    (Object.keys(STATUS_LABELS) as WorkflowStepStatus[]).map((status) => [
      status,
      steps.filter((step) => step.status === status).length,
    ]),
  ) as Record<WorkflowStepStatus, number>;
  const projectName = inline(project.projectName) || "未命名项目";
  const lines = [
    `# ${projectName} SEO 全流程报告`,
    "",
    "## 运行概览",
    "",
    `- 已完成：${counts.complete}`,
    `- 运行中：${counts.running}`,
    `- 待运行：${counts.pending}`,
    `- 已跳过：${counts.skipped}`,
    `- 等待材料：${counts.waiting}`,
    `- 失败：${counts.error}`,
  ];

  if (project.siteUrl.trim()) lines.push(`- 站点：${inline(project.siteUrl)}`);
  lines.push("", "## 分阶段结果", "");

  steps.forEach((step, index) => {
    const sequence = String(index + 1).padStart(2, "0");
    lines.push(`### ${sequence} ${MODE_LABELS[step.mode]}（${step.mode.toUpperCase()}）`, "");
    lines.push(`- 状态：${STATUS_LABELS[step.status]}`);
    if (step.createdAt) lines.push(`- 完成时间：${step.createdAt}`);
    if (step.reason?.trim()) lines.push(`- 说明：${step.reason.trim()}`);
    if (step.inputModes?.length) {
      lines.push(`- 自动继承：${step.inputModes.map((mode) => MODE_LABELS[mode]).join("、")}`);
    }
    lines.push("");

    if (step.status === "complete") {
      lines.push(step.report?.trim() || "该阶段未返回报告内容。", "");
    }
  });

  return lines.join("\n").trim();
}
