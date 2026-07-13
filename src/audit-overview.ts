export const AUDIT_ANALYSIS_KIND = "bounded_seo_artifact_inspection" as const;

export const AUDIT_SEVERITIES = ["critical", "high", "medium", "low", "info"] as const;

export type AuditSeverity = (typeof AUDIT_SEVERITIES)[number];
export type AuditGroupId = "access" | "page-signals" | "content" | "discovery" | "other";

export interface AuditScopeSummary {
  baseUrl: string | null;
  evidenceMode: string | null;
  pagesParsed: number;
  fetches: number | null;
  sitemapUrls: number | null;
}

export interface AuditFindingOverview {
  code: string | null;
  severity: AuditSeverity;
  category: string | null;
  observation: string;
  evidence: string[];
  urls: string[];
  impactBoundary: string | null;
  verification: string | null;
  confidence: string | null;
}

export interface AuditGroupOverview {
  id: AuditGroupId;
  label: string;
  description: string;
  findings: AuditFindingOverview[];
  severityCounts: Record<AuditSeverity, number>;
}

export interface AuditPageOverview {
  url: string;
  status: number | null;
  contentType: string | null;
  title: string | null;
  canonical: string | null;
  noindex: boolean | null;
  h1Count: number | null;
  depth: number | null;
  inboundLinks: number | null;
  internalLinks: number | null;
}

export interface AuditOverviewModel {
  scope: AuditScopeSummary;
  severityCounts: Record<AuditSeverity, number>;
  groups: AuditGroupOverview[];
  pages: AuditPageOverview[];
  limitations: string[];
}

interface GroupDefinition {
  id: AuditGroupId;
  label: string;
  description: string;
}

const GROUP_DEFINITIONS: readonly GroupDefinition[] = [
  {
    id: "access",
    label: "访问与抓取",
    description: "HTTP 响应、抓取控制与索引资格相关证据。",
  },
  {
    id: "page-signals",
    label: "页面与规范信号",
    description: "metadata、canonical、语言与 URL 一致性信号。",
  },
  {
    id: "content",
    label: "内容与结构",
    description: "标题结构、结构化数据、图片与页面内容信号。",
  },
  {
    id: "discovery",
    label: "站内发现",
    description: "内部链接错误、发现路径与范围内入链。",
  },
] as const;

const OTHER_GROUP: GroupDefinition = {
  id: "other",
  label: "其他证据",
  description: "尚未映射到当前四组的证据。",
};

const CATEGORY_GROUPS: Readonly<Record<string, Exclude<AuditGroupId, "other">>> = {
  http: "access",
  "crawl-control": "access",
  indexing: "access",
  metadata: "page-signals",
  "url-signals": "page-signals",
  international: "page-signals",
  "content-structure": "content",
  "structured-data": "content",
  images: "content",
  "internal-links": "discovery",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function stringValue(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(stringValue).filter((item): item is string => item !== null);
}

function metric(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : null;
}

function booleanValue(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function severityValue(value: unknown): AuditSeverity | null {
  return AUDIT_SEVERITIES.includes(value as AuditSeverity) ? value as AuditSeverity : null;
}

function emptySeverityCounts(): Record<AuditSeverity, number> {
  return { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
}

function countSeverities(findings: readonly AuditFindingOverview[]): Record<AuditSeverity, number> {
  const counts = emptySeverityCounts();
  findings.forEach((finding) => {
    counts[finding.severity] += 1;
  });
  return counts;
}

function parseFinding(value: unknown): AuditFindingOverview | null {
  if (!isRecord(value)) return null;
  const observation = stringValue(value.observation);
  const severity = severityValue(value.severity);
  if (!observation || !severity) return null;

  return {
    code: stringValue(value.code),
    severity,
    category: stringValue(value.category),
    observation,
    evidence: stringList(value.evidence),
    urls: stringList(value.urls),
    impactBoundary: stringValue(value.impact_boundary),
    verification: stringValue(value.verification),
    confidence: stringValue(value.confidence),
  };
}

function groupForFinding(finding: AuditFindingOverview): AuditGroupId {
  const code = finding.code ?? "";
  if (/^(?:http|robots|indexing|sitemap)\./i.test(code)) return "access";
  if (/^(?:canonical|metadata|language)\./i.test(code)) return "page-signals";
  if (/^(?:headings|structured-data|images)\./i.test(code)) return "content";
  if (/^links\./i.test(code)) return "discovery";
  return finding.category ? CATEGORY_GROUPS[finding.category] ?? "other" : "other";
}

function firstString(value: unknown): string | null {
  return stringList(value)[0] ?? null;
}

function linkCount(value: Record<string, unknown>, compactKey: string, fullKey: string): number | null {
  const compact = metric(value[compactKey]);
  if (compact !== null) return compact;
  return Array.isArray(value[fullKey]) ? value[fullKey].length : null;
}

function parsePage(value: unknown): AuditPageOverview | null {
  if (!isRecord(value)) return null;
  const url = stringValue(value.url) ?? stringValue(value.final_url) ?? stringValue(value.requested_url);
  if (!url) return null;

  return {
    url,
    status: metric(value.status),
    contentType: stringValue(value.content_type),
    title: firstString(value.titles),
    canonical: firstString(value.canonicals),
    noindex: booleanValue(value.noindex),
    h1Count: metric(value.h1_count),
    depth: metric(value.depth),
    inboundLinks: metric(value.inbound_links_in_scope),
    internalLinks: linkCount(value, "internal_link_count", "internal_links"),
  };
}

export function parseAuditOverview(value: unknown): AuditOverviewModel | null {
  if (!isRecord(value) || value.analysis_kind !== AUDIT_ANALYSIS_KIND) return null;

  const findings = Array.isArray(value.findings)
    ? value.findings.map(parseFinding).filter((item): item is AuditFindingOverview => item !== null)
    : [];
  const pages = Array.isArray(value.pages)
    ? value.pages.map(parsePage).filter((item): item is AuditPageOverview => item !== null)
    : [];
  const scope = isRecord(value.scope) ? value.scope : {};
  const grouped = new Map<AuditGroupId, AuditFindingOverview[]>(
    [...GROUP_DEFINITIONS, OTHER_GROUP].map((definition) => [definition.id, []]),
  );

  findings.forEach((finding) => {
    grouped.get(groupForFinding(finding))?.push(finding);
  });

  const groups = GROUP_DEFINITIONS.map((definition) => {
    const groupFindings = grouped.get(definition.id) ?? [];
    return {
      ...definition,
      findings: groupFindings,
      severityCounts: countSeverities(groupFindings),
    };
  });
  const otherFindings = grouped.get("other") ?? [];
  if (otherFindings.length > 0) {
    groups.push({
      ...OTHER_GROUP,
      findings: otherFindings,
      severityCounts: countSeverities(otherFindings),
    });
  }

  return {
    scope: {
      baseUrl: stringValue(scope.base_url),
      evidenceMode: stringValue(scope.evidence_mode),
      pagesParsed: metric(scope.pages_parsed) ?? pages.length,
      fetches: metric(scope.fetches),
      sitemapUrls: metric(scope.sitemap_urls),
    },
    severityCounts: countSeverities(findings),
    groups,
    pages,
    limitations: stringList(value.limitations),
  };
}
