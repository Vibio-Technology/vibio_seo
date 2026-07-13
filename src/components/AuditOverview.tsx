import {
  AlertTriangle,
  ChevronDown,
  CircleEllipsis,
  FileSearch,
  Globe2,
  Info,
  ListTree,
  Network,
  ShieldCheck,
} from "lucide-react";
import type { ComponentType } from "react";

import {
  AUDIT_SEVERITIES,
  parseAuditOverview,
  type AuditFindingOverview,
  type AuditGroupId,
  type AuditSeverity,
} from "../audit-overview";

interface AuditOverviewProps {
  auditReport?: Record<string, unknown>;
}

const SEVERITY_META: Record<AuditSeverity, { label: string; className: string }> = {
  critical: { label: "严重阻断", className: "border-[#d92d20] bg-[#fef3f2] text-[#b42318]" },
  high: { label: "高", className: "border-[#d65a21] bg-[#fff4ed] text-[#b54708]" },
  medium: { label: "中", className: "border-[#b7791f] bg-[#fffaeb] text-[#9a6700]" },
  low: { label: "低", className: "border-[#0f66e8] bg-[#eef6ff] text-[#0b52bd]" },
  info: { label: "信息", className: "border-[#8293a8] bg-[#f2f4f7] text-[#475467]" },
};

const FINDING_BORDER: Record<AuditSeverity, string> = {
  critical: "border-l-[#d92d20]",
  high: "border-l-[#d65a21]",
  medium: "border-l-[#b7791f]",
  low: "border-l-[#0f66e8]",
  info: "border-l-[#8293a8]",
};

const GROUP_ICONS: Record<AuditGroupId, ComponentType<{ size?: number; "aria-hidden"?: boolean }>> = {
  access: Globe2,
  "page-signals": FileSearch,
  content: ListTree,
  discovery: Network,
  other: CircleEllipsis,
};

function displayMetric(value: number | null): string {
  return value === null ? "未提供" : String(value);
}

function displayCell(value: string | number | null): string {
  return value === null || value === "" ? "—" : String(value);
}

function FindingDetails({ finding }: { finding: AuditFindingOverview }) {
  const meta = SEVERITY_META[finding.severity];
  return (
    <li className={`audit-overview__finding audit-overview__finding--${finding.severity} border border-l-[3px] border-[#d9e2ec] bg-white p-3 ${FINDING_BORDER[finding.severity]}`}>
      <div className="audit-overview__finding-header flex min-w-0 flex-wrap items-start gap-2">
        <span className={`audit-overview__label audit-overview__label--${finding.severity} inline-flex min-h-5 items-center rounded border px-1.5 text-[10px] font-semibold ${meta.className}`}>
          {meta.label}
        </span>
        <strong className="audit-overview__observation min-w-0 flex-1 text-[13px] leading-5 text-[#172033]">{finding.observation}</strong>
      </div>
      {(finding.code || finding.category) && (
        <p className="audit-overview__finding-meta mt-2 break-words font-mono text-[10px] leading-4 text-[#627084]">
          {[finding.code, finding.category].filter(Boolean).join(" / ")}
        </p>
      )}
      <dl className="audit-overview__finding-details mt-3 grid gap-3 text-[11px] leading-5 text-[#344054]">
        {finding.evidence.length > 0 && (
          <div className="audit-overview__finding-field">
            <dt className="font-semibold text-[#172033]">证据</dt>
            <dd className="mt-1">
              <ul className="audit-overview__value-list grid gap-1">
                {finding.evidence.map((item, index) => <li className="break-words" key={`${item}-${index}`}>{item}</li>)}
              </ul>
            </dd>
          </div>
        )}
        {finding.urls.length > 0 && (
          <div className="audit-overview__finding-field">
            <dt className="font-semibold text-[#172033]">URL</dt>
            <dd className="mt-1">
              <ul className="audit-overview__value-list grid gap-1">
                {finding.urls.map((url, index) => (
                  <li className="break-all font-mono text-[10px]" key={`${url}-${index}`}>{url}</li>
                ))}
              </ul>
            </dd>
          </div>
        )}
        {finding.impactBoundary && (
          <div className="audit-overview__finding-field"><dt className="font-semibold text-[#172033]">影响边界</dt><dd className="mt-1">{finding.impactBoundary}</dd></div>
        )}
        {finding.verification && (
          <div className="audit-overview__finding-field"><dt className="font-semibold text-[#172033]">复验方式</dt><dd className="mt-1">{finding.verification}</dd></div>
        )}
        {finding.confidence && (
          <div className="audit-overview__finding-field"><dt className="font-semibold text-[#172033]">置信度</dt><dd className="mt-1">{finding.confidence}</dd></div>
        )}
      </dl>
    </li>
  );
}

export function AuditOverview({ auditReport }: AuditOverviewProps) {
  const overview = parseAuditOverview(auditReport);
  if (!overview) return null;

  return (
    <section className="audit-overview grid gap-6 text-[#172033]" aria-label="确定性审计概览">
      <header className="audit-overview__header grid gap-2">
        <span className="audit-overview__eyebrow font-mono text-[10px] font-semibold text-[#0b52bd]">BOUNDED SEO EVIDENCE</span>
        <h2 className="audit-overview__title m-0 text-xl font-bold leading-7">审计概览</h2>
        <p className="audit-overview__intro m-0 max-w-3xl text-xs leading-5 text-[#627084]">
          以下只是当前有界证据的结构化展示，不生成健康分或等级，不证明搜索引擎已抓取、已收录或会产生 AI 引用。
        </p>
      </header>

      <dl className="audit-overview__scope grid grid-cols-1 border-y border-[#d9e2ec] bg-[#f9fbfd] sm:grid-cols-3">
        {[
          ["已解析页面", overview.scope.pagesParsed],
          ["HTTP 请求", overview.scope.fetches],
          ["Sitemap URL", overview.scope.sitemapUrls],
        ].map(([label, value], index) => (
          <div className={`audit-overview__metric p-3 ${index > 0 ? "border-t border-[#d9e2ec] sm:border-l sm:border-t-0" : ""}`} key={label}>
            <dt className="audit-overview__metric-label text-[10px] font-semibold text-[#627084]">{label}</dt>
            <dd className="audit-overview__metric-value mt-1 text-lg font-bold tabular-nums">{displayMetric(value as number | null)}</dd>
          </div>
        ))}
      </dl>

      {(overview.scope.baseUrl || overview.scope.evidenceMode) && (
        <div className="audit-overview__scope-meta flex min-w-0 flex-wrap gap-x-5 gap-y-2 text-[10px] text-[#627084]">
          {overview.scope.baseUrl && <span className="break-all font-mono">基准 URL：{overview.scope.baseUrl}</span>}
          {overview.scope.evidenceMode && <span>证据模式：{overview.scope.evidenceMode}</span>}
        </div>
      )}

      <section className="audit-overview__severity" aria-labelledby="audit-severity-title">
        <h3 className="audit-overview__section-title m-0 text-sm font-bold" id="audit-severity-title">严重度计数</h3>
        <ul className="audit-overview__severity-list mt-3 flex flex-wrap gap-2" aria-label="按严重度统计的发现">
          {AUDIT_SEVERITIES.map((severity) => {
            const meta = SEVERITY_META[severity];
            return (
              <li className={`audit-overview__severity-item audit-overview__severity-item--${severity} inline-flex min-h-7 items-center gap-2 rounded border px-2 text-[11px] ${meta.className}`} key={severity}>
                <span>{meta.label}</span>
                <strong className="audit-overview__severity-count tabular-nums">{overview.severityCounts[severity]}</strong>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="audit-overview__group-section" aria-labelledby="audit-groups-title">
        <div className="audit-overview__section-heading flex items-center justify-between gap-3">
          <h3 className="audit-overview__section-title m-0 text-sm font-bold" id="audit-groups-title">证据分组</h3>
          <span className="audit-overview__section-count text-[10px] text-[#627084]">共 {overview.groups.reduce((sum, group) => sum + group.findings.length, 0)} 条</span>
        </div>
        <div className="audit-overview__groups mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {overview.groups.map((group) => {
            const Icon = GROUP_ICONS[group.id];
            return (
              <article className="audit-overview__group min-w-0 rounded-lg border border-[#d9e2ec] bg-white p-4" key={group.id}>
                <header className="audit-overview__group-header grid grid-cols-[36px_minmax(0,1fr)_auto] items-start gap-3">
                  <span className="audit-overview__group-icon inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[#eef6ff] text-[#0f66e8]">
                    <Icon size={18} aria-hidden={true} />
                  </span>
                  <div className="audit-overview__group-copy min-w-0">
                    <h4 className="audit-overview__group-title m-0 text-sm font-bold">{group.label}</h4>
                    <p className="audit-overview__group-description mt-1 text-[10px] leading-4 text-[#627084]">{group.description}</p>
                  </div>
                  <strong className="audit-overview__group-count text-lg tabular-nums">{group.findings.length}</strong>
                </header>

                {group.findings.length > 0 ? (
                  <details className="audit-overview__group-details group mt-4 border-t border-[#d9e2ec] pt-3">
                    <summary className="audit-overview__group-summary flex min-h-8 cursor-pointer list-none items-center justify-between gap-2 text-[11px] font-semibold text-[#0b52bd] [&::-webkit-details-marker]:hidden">
                      <span>展开 {group.findings.length} 条发现</span>
                      <ChevronDown className="transition-transform group-open:rotate-180" size={16} aria-hidden="true" />
                    </summary>
                    <ul className="audit-overview__findings mt-2 grid gap-2">
                      {group.findings.map((finding, index) => (
                        <FindingDetails finding={finding} key={`${finding.code ?? finding.observation}-${index}`} />
                      ))}
                    </ul>
                  </details>
                ) : (
                  <p className="audit-overview__empty mt-4 border-t border-[#d9e2ec] pt-3 text-[10px] text-[#627084]">
                    当前有界范围没有映射到该组的发现。
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </section>

      <section className="audit-overview__pages-section" aria-labelledby="audit-pages-title">
        <div className="audit-overview__section-heading flex items-center justify-between gap-3">
          <h3 className="audit-overview__section-title m-0 text-sm font-bold" id="audit-pages-title">页面核验表</h3>
          <span className="audit-overview__section-count text-[10px] text-[#627084]">已展示 {overview.pages.length} 页</span>
        </div>
        {overview.pages.length > 0 ? (
          <div className="audit-overview__pages mt-3 overflow-x-auto rounded-lg border border-[#d9e2ec]">
            <table className="audit-overview__table w-full min-w-[980px] border-collapse bg-white text-left text-[11px]">
              <caption className="sr-only">当前有界审计范围中的页面核验结果</caption>
              <thead className="bg-[#f9fbfd] text-[10px] text-[#627084]">
                <tr>
                  {["URL", "状态", "类型", "Title", "Canonical", "Noindex", "H1", "深度", "范围内入链", "内链"].map((heading) => (
                    <th className="border-b border-[#d9e2ec] px-3 py-2 font-semibold" scope="col" key={heading}>{heading}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {overview.pages.map((page, index) => (
                  <tr className="border-b border-[#d9e2ec] last:border-b-0" key={`${page.url}-${index}`}>
                    <td className="max-w-64 break-all px-3 py-2 font-mono text-[10px]">{page.url}</td>
                    <td className="px-3 py-2 tabular-nums">{displayCell(page.status)}</td>
                    <td className="px-3 py-2">{displayCell(page.contentType)}</td>
                    <td className="max-w-48 break-words px-3 py-2">{displayCell(page.title)}</td>
                    <td className="max-w-64 break-all px-3 py-2 font-mono text-[10px]">{displayCell(page.canonical)}</td>
                    <td className="px-3 py-2">{page.noindex === null ? "未知" : page.noindex ? "是" : "否"}</td>
                    <td className="px-3 py-2 tabular-nums">{displayCell(page.h1Count)}</td>
                    <td className="px-3 py-2 tabular-nums">{displayCell(page.depth)}</td>
                    <td className="px-3 py-2 tabular-nums">{displayCell(page.inboundLinks)}</td>
                    <td className="px-3 py-2 tabular-nums">{displayCell(page.internalLinks)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="audit-overview__empty mt-3 rounded-lg border border-[#d9e2ec] bg-[#f9fbfd] p-3 text-[11px] text-[#627084]">
            报告没有提供可展示的页面记录。
          </p>
        )}
      </section>

      <section className="audit-overview__limitations" aria-labelledby="audit-limitations-title">
        <div className="audit-overview__section-heading flex items-center gap-2">
          <ShieldCheck size={17} className="text-[#0f66e8]" aria-hidden="true" />
          <h3 className="audit-overview__section-title m-0 text-sm font-bold" id="audit-limitations-title">证据边界</h3>
        </div>
        {overview.limitations.length > 0 ? (
          <ul className="audit-overview__limitations-list mt-3 grid gap-2">
            {overview.limitations.map((limitation, index) => (
              <li className="audit-overview__boundary flex items-start gap-2 rounded-lg border border-[#d9e2ec] bg-[#f9fbfd] p-3 text-[11px] leading-5 text-[#475467]" key={`${limitation}-${index}`}>
                <Info size={15} className="mt-0.5 shrink-0 text-[#0f66e8]" aria-hidden="true" />
                <span>{limitation}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="audit-overview__boundary audit-overview__boundary--warning mt-3 flex items-start gap-2 rounded-lg border border-[#f3d19e] bg-[#fff7e6] p-3 text-[11px] leading-5 text-[#7a5b14]">
            <AlertTriangle size={15} className="mt-0.5 shrink-0" aria-hidden="true" />
            报告未提供 limitations；不应因此扩大当前证据的结论范围。
          </p>
        )}
      </section>
    </section>
  );
}
