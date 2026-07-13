import {
  Check,
  ArrowRight,
  Clipboard,
  Code2,
  Download,
  FileCode2,
  FileText,
  LayoutDashboard,
  RotateCcw,
  SearchCheck,
  Workflow,
} from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { parseAuditOverview } from "../audit-overview";
import { buildStandaloneReportHtml } from "../report-export";
import type { RunRecord } from "../types";
import { AuditOverview } from "./AuditOverview";
import { WorkflowProgress } from "./WorkflowProgress";

interface ReportViewProps {
  record: RunRecord;
  onReset: () => void;
  nextAction?: {
    label: string;
    description: string;
    onContinue: () => void;
    disabled?: boolean;
  };
}

function download(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

function safeFileName(value: string): string {
  return value.trim().replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]+/g, "-").slice(0, 48) || "vibio-report";
}

export function ReportView({ record, onReset, nextAction }: ReportViewProps) {
  type ReportTab = "overview" | "report" | "workflow" | "evidence";
  const hasAuditOverview = parseAuditOverview(record.auditReport) !== null;
  const defaultTab: ReportTab = hasAuditOverview ? "overview" : "report";
  const [tab, setTab] = useState<ReportTab>(defaultTab);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "error">("idle");
  const titleRef = useRef<HTMLHeadingElement>(null);
  const overviewRef = useRef<HTMLDivElement>(null);
  const reportRef = useRef<HTMLElement>(null);
  const tabRefs = useRef<Partial<Record<ReportTab, HTMLButtonElement | null>>>({});
  const baseName = `${safeFileName(record.projectName)}-${record.mode}-${record.createdAt.slice(0, 10)}`;
  const tabs: ReportTab[] = [
    ...(hasAuditOverview ? ["overview" as const] : []),
    "report",
    ...(record.workflow ? ["workflow" as const] : []),
    "evidence",
  ];

  useEffect(() => {
    setTab(hasAuditOverview ? "overview" : "report");
    titleRef.current?.focus({ preventScroll: true });
  }, [hasAuditOverview, record.id]);

  const selectTab = (next: ReportTab) => {
    setTab(next);
    window.requestAnimationFrame(() => tabRefs.current[next]?.focus());
  };

  const handleTabKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const current = tabs.indexOf(tab);
    const next = event.key === "Home"
      ? 0
      : event.key === "End"
        ? tabs.length - 1
        : (current + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    selectTab(tabs[next]);
  };

  const copyReport = async () => {
    try {
      await navigator.clipboard.writeText(record.report);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("error");
    }
    window.setTimeout(() => setCopyStatus("idle"), 1600);
  };

  const jsonExport = JSON.stringify(
    {
      schema_version: "vibio-web.run.v1",
      ...record,
    },
    null,
    2,
  );

  const exportHtml = () => {
    const html = buildStandaloneReportHtml(
      record,
      overviewRef.current?.innerHTML ?? "",
      reportRef.current?.innerHTML ?? "",
    );
    download(`${baseName}.html`, html, "text/html;charset=utf-8");
  };

  return (
    <section className="report-view" aria-labelledby="report-title">
      <header className="report-header">
        <div>
          <span className="eyebrow">运行完成 · {record.provider} / {record.model}</span>
          <h1 id="report-title" ref={titleRef} tabIndex={-1}>{record.projectName}</h1>
          <p>{record.objective}</p>
        </div>
        <div className="report-actions">
          <button type="button" className="icon-button" onClick={copyReport} title="复制 Markdown">
            {copyStatus === "copied" ? <Check size={17} /> : <Clipboard size={17} />}
            <span>{copyStatus === "copied" ? "已复制" : copyStatus === "error" ? "复制失败" : "复制"}</span>
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => download(`${baseName}.md`, record.report, "text/markdown;charset=utf-8")}
            title="下载 Markdown"
          >
            <Download size={17} />
            <span>Markdown</span>
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={() => download(`${baseName}.json`, jsonExport, "application/json;charset=utf-8")}
            title="下载 JSON"
          >
            <Code2 size={17} />
            <span>JSON</span>
          </button>
          <button
            type="button"
            className="icon-button"
            onClick={exportHtml}
            aria-label="下载独立 HTML 报告"
            title="下载独立 HTML 报告"
          >
            <FileCode2 size={17} />
            <span>HTML</span>
          </button>
          <button type="button" className="icon-button icon-button--primary" onClick={onReset}>
            <RotateCcw size={17} />
            <span>新建运行</span>
          </button>
        </div>
      </header>

      <div className="report-meta">
        <span>{record.market}</span>
        <span>{record.language}</span>
        <span>{record.siteUrl || "无公开 URL"}</span>
        <time dateTime={record.createdAt}>{new Date(record.createdAt).toLocaleString("zh-CN")}</time>
      </div>

      <div
        className="report-tabs"
        role="tablist"
        aria-label="报告视图"
        onKeyDown={handleTabKeyDown}
      >
        {hasAuditOverview && (
          <button
            type="button"
            role="tab"
            id="report-tab-overview"
            aria-controls="report-panel-overview"
            aria-selected={tab === "overview"}
            tabIndex={tab === "overview" ? 0 : -1}
            ref={(element) => { tabRefs.current.overview = element; }}
            className={tab === "overview" ? "is-active" : ""}
            onClick={() => selectTab("overview")}
          >
            <LayoutDashboard size={16} />
            审计概览
          </button>
        )}
        <button
          type="button"
          role="tab"
          id="report-tab-report"
          aria-controls="report-panel-report"
          aria-selected={tab === "report"}
          tabIndex={tab === "report" ? 0 : -1}
          ref={(element) => { tabRefs.current.report = element; }}
          className={tab === "report" ? "is-active" : ""}
          onClick={() => selectTab("report")}
        >
          <FileText size={16} />
          分析报告
        </button>
        {record.workflow && (
          <button
            type="button"
            role="tab"
            id="report-tab-workflow"
            aria-controls="report-panel-workflow"
            aria-selected={tab === "workflow"}
            tabIndex={tab === "workflow" ? 0 : -1}
            ref={(element) => { tabRefs.current.workflow = element; }}
            className={tab === "workflow" ? "is-active" : ""}
            onClick={() => selectTab("workflow")}
          >
            <Workflow size={16} />
            流程轨迹
          </button>
        )}
        <button
          type="button"
          role="tab"
          id="report-tab-evidence"
          aria-controls="report-panel-evidence"
          aria-selected={tab === "evidence"}
          tabIndex={tab === "evidence" ? 0 : -1}
          ref={(element) => { tabRefs.current.evidence = element; }}
          className={tab === "evidence" ? "is-active" : ""}
          onClick={() => selectTab("evidence")}
        >
          <SearchCheck size={16} />
          证据清单
        </button>
      </div>

      {nextAction && (
        <aside className="report-next-action" aria-label="推荐下一步">
          <div>
            <span className="eyebrow">链式下一步</span>
            <strong>{nextAction.description}</strong>
          </div>
          <button
            type="button"
            className="run-button"
            onClick={nextAction.onContinue}
            disabled={nextAction.disabled}
          >
            <Workflow size={18} aria-hidden="true" />
            <span>{nextAction.label}</span>
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </aside>
      )}

      {hasAuditOverview && (
        <div
          className="audit-overview-panel"
          role="tabpanel"
          id="report-panel-overview"
          aria-labelledby="report-tab-overview"
          tabIndex={0}
          hidden={tab !== "overview"}
          ref={overviewRef}
        >
          <AuditOverview auditReport={record.auditReport} />
        </div>
      )}

      <article
        className="markdown-report"
        role="tabpanel"
        id="report-panel-report"
        aria-labelledby="report-tab-report"
        tabIndex={0}
        hidden={tab !== "report"}
        ref={reportRef}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{record.report}</ReactMarkdown>
      </article>

      {record.workflow && (
        <div
          className="workflow-report"
          role="tabpanel"
          id="report-panel-workflow"
          aria-labelledby="report-tab-workflow"
          tabIndex={0}
          hidden={tab !== "workflow"}
        >
          <WorkflowProgress steps={record.workflow.steps} compact />
        </div>
      )}

      <div
        className="evidence-report"
        role="tabpanel"
        id="report-panel-evidence"
        aria-labelledby="report-tab-evidence"
        tabIndex={0}
        hidden={tab !== "evidence"}
      >
        <div className="evidence-manifest">
          <h2>输入来源</h2>
          {record.siteUrl && (
            <div className="manifest-row">
              <GlobeManifestIcon />
              <div><strong>公开 URL</strong><span>{record.siteUrl}</span></div>
            </div>
          )}
          {record.evidence.map((file) => (
            <div className="manifest-row" key={file.name}>
              <FileText size={16} />
              <div><strong>{file.name}</strong><span>{Math.round(file.size / 1024)} KB · {file.type}</span></div>
            </div>
          ))}
          {!record.siteUrl && record.evidence.length === 0 && <p>本次运行没有附加外部证据。</p>}
        </div>
        {record.auditReport && (
          <details className="raw-evidence">
            <summary>查看确定性审计 JSON</summary>
            <pre>{JSON.stringify(record.auditReport, null, 2)}</pre>
          </details>
        )}
      </div>
    </section>
  );
}

function GlobeManifestIcon() {
  return <span className="manifest-globe" aria-hidden="true">URL</span>;
}
