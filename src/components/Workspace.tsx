"use client";

import {
  ArrowRight,
  Database,
  History,
  Play,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useRef, useState } from "react";
import { EMPTY_PROJECT, FALLBACK_PROVIDERS, MODES } from "../data";
import {
  clearRuns,
  loadModelSettings,
  loadProject,
  loadRuns,
  saveModelSettings,
  saveProject,
  saveRun,
} from "../storage";
import type {
  AnalysisResponse,
  ApiErrorPayload,
  EvidenceFile,
  InspectResponse,
  ModeId,
  ModelSettings,
  ProjectInput,
  ProviderDefinition,
  RunRecord,
  RunStage,
} from "../types";
import { EvidencePanel } from "./EvidencePanel";
import { HistoryDrawer } from "./HistoryDrawer";
import { ModeRail } from "./ModeRail";
import { ProjectForm } from "./ProjectForm";
import { ProviderPanel } from "./ProviderPanel";
import { ReportView } from "./ReportView";
import { RunStatus } from "./RunStatus";

const DEFAULT_SETTINGS: ModelSettings = {
  provider: FALLBACK_PROVIDERS[0].id,
  model: FALLBACK_PROVIDERS[0].default_model,
  apiKey: "",
};

const INSPECT_MODES = new Set<ModeId>(["audit", "fix", "review", "recover", "plan", "link"]);

async function readApiError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as ApiErrorPayload;
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg).filter(Boolean).join("；") || `请求失败（${response.status}）`;
    }
    if (payload.detail && typeof payload.detail === "object" && payload.detail.message) {
      return payload.detail.message;
    }
    return payload.message ?? `请求失败（${response.status}）`;
  } catch {
    return `请求失败（${response.status}）`;
  }
}

function validateProject(project: ProjectInput, settings: ModelSettings): string | null {
  if (!project.projectName.trim()) return "请填写项目名称。";
  if (!project.market.trim()) return "请填写目标国家或地区。";
  if (!project.language.trim()) return "请填写目标语言。";
  if (!project.conversion.trim()) return "请定义主要合格转化。";
  if (!project.objective.trim()) return "请填写本次目标或问题。";
  if (project.siteUrl) {
    try {
      const url = new URL(project.siteUrl);
      if (!['http:', 'https:'].includes(url.protocol)) return "站点 URL 必须使用 HTTP 或 HTTPS。";
    } catch {
      return "站点 URL 格式不正确。";
    }
  }
  if (!settings.apiKey.trim()) return "请输入所选模型提供商的 API Key。";
  if (!settings.model.trim()) return "请输入模型 ID。";
  return null;
}

export function Workspace() {
  const [modeId, setModeId] = useState<ModeId>("audit");
  const [project, setProject] = useState<ProjectInput>(EMPTY_PROJECT);
  const [providers, setProviders] = useState<ProviderDefinition[]>(FALLBACK_PROVIDERS);
  const [settings, setSettings] = useState<ModelSettings>(DEFAULT_SETTINGS);
  const [evidence, setEvidence] = useState<EvidenceFile[]>([]);
  const [maxPages, setMaxPages] = useState(6);
  const [stage, setStage] = useState<RunStage>("idle");
  const [error, setError] = useState("");
  const [record, setRecord] = useState<RunRecord | null>(null);
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const runLock = useRef(false);

  const mode = useMemo(
    () => MODES.find((item) => item.id === modeId) ?? MODES[0],
    [modeId],
  );
  const running = ["validating", "collecting", "analyzing"].includes(stage);

  useEffect(() => {
    setProject(loadProject(EMPTY_PROJECT));
    setSettings(loadModelSettings(DEFAULT_SETTINGS));
    setRuns(loadRuns());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveProject(project);
  }, [hydrated, project]);

  useEffect(() => {
    if (hydrated) saveModelSettings(settings);
  }, [hydrated, settings]);

  useEffect(() => {
    const controller = new AbortController();
    void fetch("/api/providers", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("provider catalog unavailable");
        const payload = (await response.json()) as { providers?: ProviderDefinition[] } | ProviderDefinition[];
        const items = Array.isArray(payload) ? payload : payload.providers;
        if (items?.length) setProviders(items);
        setApiConnected(true);
      })
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setApiConnected(false);
      });
    return () => controller.abort();
  }, []);

  const changeMode = (nextMode: ModeId) => {
    setModeId(nextMode);
    setRecord(null);
    setStage("idle");
    setError("");
  };

  const runAnalysis = async () => {
    if (runLock.current) return;
    runLock.current = true;
    const runProject = { ...project };
    const runSettings = { ...settings };
    const runModeId = modeId;
    const runMaxPages = maxPages;
    const runEvidence = evidence.map((file) => ({ ...file }));
    const validationError = validateProject(runProject, runSettings);
    if (validationError) {
      setError(validationError);
      setStage("error");
      runLock.current = false;
      return;
    }

    setError("");
    setStage("validating");
    setRecord(null);

    let auditReport: Record<string, unknown> | undefined;
    const shouldInspect = Boolean(
      runProject.siteUrl && runProject.allowNetworkEvidence && INSPECT_MODES.has(runModeId),
    );

    try {
      if (shouldInspect) {
        setStage("collecting");
        const inspectResponse = await fetch("/api/inspect", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Vibio-Api-Key": runSettings.apiKey,
          },
          body: JSON.stringify({
            url: runProject.siteUrl,
            max_pages: runMaxPages,
            production: false,
          }),
        });
        if (inspectResponse.ok) {
          const inspection = (await inspectResponse.json()) as InspectResponse;
          auditReport = inspection.report;
        } else {
          auditReport = {
            evidence_status: "unavailable",
            reason: await readApiError(inspectResponse),
          };
        }
      }

      setStage("analyzing");
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Vibio-Api-Key": runSettings.apiKey,
        },
        body: JSON.stringify({
          provider: runSettings.provider,
          model: runSettings.model,
          mode: runModeId,
          project: runProject,
          evidence: runEvidence.map(({ id: _id, ...file }) => file),
          audit_report: auditReport,
        }),
      });

      if (!response.ok) throw new Error(await readApiError(response));
      const result = (await response.json()) as AnalysisResponse;
      const createdAt = result.created_at || new Date().toISOString();
      const nextRecord: RunRecord = {
        id: crypto.randomUUID(),
        mode: runModeId,
        projectName: runProject.projectName,
        siteUrl: runProject.siteUrl,
        market: runProject.market,
        language: runProject.language,
        objective: runProject.objective,
        provider: result.provider || runSettings.provider,
        model: result.model || runSettings.model,
        report: result.report,
        auditReport,
        evidence: runEvidence.map(({ name, type, size }) => ({ name, type, size })),
        createdAt,
      };
      setRecord(nextRecord);
      setRuns(saveRun(nextRecord));
      setStage("complete");
      setApiConnected(true);
    } catch (runError) {
      const message = runError instanceof Error ? runError.message : "运行失败，请稍后重试。";
      setError(message);
      setStage("error");
    } finally {
      runLock.current = false;
    }
  };

  const resetRun = () => {
    setRecord(null);
    setStage("idle");
    setError("");
  };

  return (
    <div className="app-frame">
      <header className="topbar">
        <div className="brand-lockup">
          <Image src="/vibio-logo.png" alt="Vibio" width={37} height={37} priority />
          <div>
            <strong>Vibio SEO</strong>
            <span>Evidence Workspace</span>
          </div>
        </div>
        <div className="topbar__meta">
          <div className={`api-state${apiConnected === false ? " is-offline" : ""}`}>
            <span className="status-dot" />
            <span>{apiConnected === false ? "本地界面" : apiConnected ? "服务已连接" : "检查服务"}</span>
          </div>
          <span className="version-mark">V5.0</span>
          <button type="button" className="icon-button" onClick={() => setHistoryOpen(true)}>
            <History size={17} />
            <span>运行记录</span>
            {runs.length > 0 && <span className="button-count">{runs.length}</span>}
          </button>
        </div>
      </header>

      <div className="workspace-grid">
        <ModeRail modes={MODES} activeMode={modeId} onChange={changeMode} disabled={running} />

        <main className="main-workspace">
          <RunStatus stage={stage} />
          {error && (
            <div className="error-banner" role="alert">
              <TriangleAlert size={17} />
              <span>{error}</span>
              <button type="button" onClick={() => setError("")} aria-label="关闭错误提示">关闭</button>
            </div>
          )}

          {record ? (
            <ReportView record={record} onReset={resetRun} />
          ) : (
            <>
              <ProjectForm mode={mode} project={project} onChange={setProject} disabled={running} />
              <footer className="run-bar">
                <div className="run-bar__contract">
                  <Sparkles size={17} aria-hidden="true" />
                  <div>
                    <span>本次交付</span>
                    <strong>{mode.output}</strong>
                  </div>
                </div>
                <button
                  type="button"
                  className="run-button"
                  onClick={() => void runAnalysis()}
                  disabled={running}
                >
                  {running ? <Sparkles size={18} className="pulse" /> : <Play size={18} fill="currentColor" />}
                  <span>{running ? "正在运行" : `运行${mode.label}`}</span>
                  {!running && <ArrowRight size={17} />}
                </button>
              </footer>
            </>
          )}
        </main>

        <aside className="context-panel" aria-label="模型与证据设置">
          <ProviderPanel
            providers={providers}
            settings={settings}
            onChange={setSettings}
            loading={running}
          />
          <EvidencePanel
            mode={mode}
            files={evidence}
            onChange={setEvidence}
            siteUrl={project.siteUrl}
            networkEnabled={project.allowNetworkEvidence}
            maxPages={maxPages}
            onMaxPagesChange={setMaxPages}
            onError={(message) => {
              setError(message);
              setStage("error");
            }}
            disabled={running}
          />
          <section className="side-section boundary-panel" aria-labelledby="boundary-heading">
            <div className="side-section__heading">
              <div>
                <span className="eyebrow">运行边界</span>
                <h2 id="boundary-heading">只读与可审阅</h2>
              </div>
              <ShieldCheck size={18} />
            </div>
            <ul>
              <li><Database size={14} />报告历史仅存当前浏览器</li>
              <li><ShieldCheck size={14} />不自动部署、不发外联、不投广告</li>
            </ul>
          </section>
        </aside>
      </div>

      <HistoryDrawer
        open={historyOpen}
        runs={runs}
        modes={MODES}
        onClose={() => setHistoryOpen(false)}
        onSelect={(selected) => {
          setRecord(selected);
          setModeId(selected.mode);
          setStage("complete");
          setHistoryOpen(false);
          setError("");
        }}
        onClear={() => {
          clearRuns();
          setRuns([]);
        }}
      />
    </div>
  );
}
