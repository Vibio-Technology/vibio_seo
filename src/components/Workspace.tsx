"use client";

import {
  ArrowRight,
  Database,
  History,
  Play,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Workflow,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { EMPTY_WORKSPACE_DRAFT, FALLBACK_PROVIDERS, MODES } from "../data";
import {
  clearRuns,
  loadModelSettings,
  loadRuns,
  loadWorkspaceDraft,
  saveModelSettings,
  saveRun,
  saveWorkspaceDraft,
} from "../storage";
import type {
  AnalysisResponse,
  ApiErrorPayload,
  EvidenceFile,
  InspectResponse,
  ModeId,
  ModeDefinition,
  ModelSettings,
  ProjectInput,
  ProjectProfile,
  ProviderDefinition,
  RunRecord,
  RunStage,
  WorkspaceDraftV2,
  WorkflowStep,
} from "../types";
import {
  aggregateWorkflowMarkdown,
  buildWorkflowContext,
  buildWorkflowPlan,
} from "../workflow";
import {
  buildAnalysisProject,
} from "../workspace-draft";
import { EvidencePanel } from "./EvidencePanel";
import { HistoryDrawer } from "./HistoryDrawer";
import { ModeTaskForm } from "./ModeTaskForm";
import { ModeRail } from "./ModeRail";
import { ProjectSetup } from "./ProjectSetup";
import { ProviderPanel } from "./ProviderPanel";
import { ReportView } from "./ReportView";
import { RunStatus } from "./RunStatus";
import { WorkflowProgress } from "./WorkflowProgress";

const DEFAULT_SETTINGS: ModelSettings = {
  provider: FALLBACK_PROVIDERS[0].id,
  model: FALLBACK_PROVIDERS[0].default_model,
  apiKey: "",
};

const INSPECT_MODES = new Set<ModeId>(["audit", "fix", "review", "recover", "plan", "link"]);

type ExecutionKind = "single" | "workflow";

interface WorkflowExecution {
  signature: string;
  startedAt: string;
  inspectionComplete: boolean;
  auditReport?: Record<string, unknown>;
  steps: WorkflowStep[];
}

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

function validateProjectProfile(profile: ProjectProfile): string | null {
  if (!profile.projectName.trim()) return "请填写项目名称。";
  if (!profile.market.trim()) return "请填写目标国家或地区。";
  if (!profile.language.trim()) return "请填写目标语言。";
  if (!profile.conversion.trim()) return "请定义主要合格转化。";
  if (!profile.primaryGoal.trim()) return "请填写项目主要目标。";
  if (profile.siteUrl) {
    try {
      const url = new URL(profile.siteUrl);
      if (!['http:', 'https:'].includes(url.protocol)) return "站点 URL 必须使用 HTTP 或 HTTPS。";
    } catch {
      return "站点 URL 格式不正确。";
    }
  }
  return null;
}

function validateModelSettings(settings: ModelSettings): string | null {
  if (!settings.apiKey.trim()) return "请输入所选模型提供商的 API Key。";
  if (!settings.model.trim()) return "请输入模型 ID。";
  return null;
}

function validateModeTask(draft: WorkspaceDraftV2, mode: ModeDefinition): string | null {
  const task = draft.modes[mode.id];
  const requiredFields = ["objective", "details", "scope", "timing"] as const;
  for (const field of requiredFields) {
    const definition = mode.task[field];
    if (definition?.required && !task[field].trim()) {
      return `请填写“${definition.label}”。`;
    }
  }
  return null;
}

function projectProfileIsComplete(profile: ProjectProfile): boolean {
  return validateProjectProfile(profile) === null;
}

function cloneWorkspaceDraft(draft: WorkspaceDraftV2): WorkspaceDraftV2 {
  return {
    schemaVersion: 2,
    profile: { ...draft.profile },
    modes: Object.fromEntries(
      MODES.map(({ id }) => [id, { ...draft.modes[id] }]),
    ) as WorkspaceDraftV2["modes"],
    sharedContext: draft.sharedContext,
  };
}

function workflowInputSignature(
  draft: WorkspaceDraftV2,
  settings: ModelSettings,
  evidence: EvidenceFile[],
  maxPages: number,
): string {
  return JSON.stringify({
    draft,
    provider: settings.provider,
    model: settings.model,
    maxPages,
    evidence: evidence.map(({ id: _id, ...file }) => file),
  });
}

function inspectionUnavailable(report: Record<string, unknown> | undefined): boolean {
  return report?.evidence_status === "unavailable";
}

function scrollPageTop(): void {
  window.requestAnimationFrame(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  });
}

async function inspectSite(
  project: ProjectInput,
  settings: ModelSettings,
  maxPages: number,
): Promise<Record<string, unknown>> {
  const response = await fetch("/api/inspect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Vibio-Api-Key": settings.apiKey,
    },
    body: JSON.stringify({
      url: project.siteUrl,
      max_pages: maxPages,
      production: false,
    }),
  });
  if (!response.ok) {
    return {
      evidence_status: "unavailable",
      reason: await readApiError(response),
    };
  }
  const inspection = (await response.json()) as InspectResponse;
  return inspection.report;
}

async function analyzeMode({
  mode,
  project,
  settings,
  evidence,
  auditReport,
  workflowContext,
}: {
  mode: ModeId;
  project: ProjectInput;
  settings: ModelSettings;
  evidence: EvidenceFile[];
  auditReport?: Record<string, unknown>;
  workflowContext?: unknown;
}): Promise<AnalysisResponse> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Vibio-Api-Key": settings.apiKey,
    },
    body: JSON.stringify({
      provider: settings.provider,
      model: settings.model,
      mode,
      project,
      evidence: evidence.map(({ id: _id, ...file }) => file),
      audit_report: auditReport,
      ...(workflowContext === undefined ? {} : { workflow_context: workflowContext }),
    }),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as AnalysisResponse;
}

export function Workspace() {
  const [modeId, setModeId] = useState<ModeId>("audit");
  const [workspaceDraft, setWorkspaceDraft] = useState<WorkspaceDraftV2>(EMPTY_WORKSPACE_DRAFT);
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
  const [executionKind, setExecutionKind] = useState<ExecutionKind | null>(null);
  const [workflowSteps, setWorkflowSteps] = useState<WorkflowStep[]>([]);
  const [editingProject, setEditingProject] = useState(false);
  const [projectEstablished, setProjectEstablished] = useState(false);
  const runLock = useRef(false);
  const workflowExecution = useRef<WorkflowExecution | null>(null);

  const mode = useMemo(
    () => MODES.find((item) => item.id === modeId) ?? MODES[0],
    [modeId],
  );
  const profileReady = projectProfileIsComplete(workspaceDraft.profile);
  const workspaceActive = hydrated && projectEstablished && profileReady;
  const showingProjectSetup = !projectEstablished || editingProject;
  const running = ["validating", "collecting", "analyzing"].includes(stage);
  const workflowRunning = running && executionKind === "workflow";
  const singleRunning = running && executionKind === "single";
  const failedWorkflowStep = workflowSteps.find((step) => step.status === "error");
  const currentWorkflowSignature = useMemo(
    () => workflowInputSignature(workspaceDraft, settings, evidence, maxPages),
    [evidence, maxPages, settings.model, settings.provider, workspaceDraft],
  );
  const workflowCanResume = Boolean(
    failedWorkflowStep &&
    workflowExecution.current?.signature === currentWorkflowSignature,
  );
  const workflowWillRetryInspection = Boolean(
    workflowCanResume &&
    workflowExecution.current?.inspectionComplete === false &&
    workspaceDraft.profile.siteUrl &&
    workspaceDraft.profile.allowNetworkEvidence,
  );
  const workflowAnalysisLabel = useMemo(() => {
    const runnable = workflowSteps.filter((step) => step.status !== "skipped");
    const current = runnable.findIndex((step) => step.status === "running");
    if (current < 0) return undefined;
    const modeLabel = MODES.find((item) => item.id === runnable[current].mode)?.label;
    return `能力链 ${current + 1}/${runnable.length} · ${modeLabel ?? runnable[current].mode}`;
  }, [workflowSteps]);
  const workflowContract = useMemo(() => {
    const completed = workflowSteps.filter((step) => step.status === "complete").length;
    const skipped = workflowSteps.filter((step) => step.status === "skipped").length;
    if (failedWorkflowStep) {
      const label = MODES.find((item) => item.id === failedWorkflowStep.mode)?.label;
      return workflowWillRetryInspection
        ? "URL 证据将重试 · 恢复后重算已完成阶段"
        : workflowCanResume
          ? `已完成 ${completed} 步 · 可从${label ?? failedWorkflowStep.mode}继续`
        : "输入已变化 · 将从头重新运行";
    }
    return `已完成 ${completed} 步 · 条件跳过 ${skipped} 步`;
  }, [failedWorkflowStep, workflowCanResume, workflowSteps, workflowWillRetryInspection]);

  useEffect(() => {
    const storedDraft = loadWorkspaceDraft(EMPTY_WORKSPACE_DRAFT);
    setWorkspaceDraft(storedDraft);
    setProjectEstablished(projectProfileIsComplete(storedDraft.profile));
    setSettings(loadModelSettings(DEFAULT_SETTINGS));
    setRuns(loadRuns());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveWorkspaceDraft(workspaceDraft);
  }, [hydrated, workspaceDraft]);

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
    setWorkflowSteps([]);
    workflowExecution.current = null;
  };

  const runAnalysis = async () => {
    if (runLock.current) return;
    runLock.current = true;
    const runDraft = cloneWorkspaceDraft(workspaceDraft);
    const runModeId = modeId;
    const runMode = MODES.find((item) => item.id === runModeId) ?? MODES[0];
    const runProject = buildAnalysisProject(runDraft, runModeId);
    const runSettings = { ...settings };
    const runMaxPages = maxPages;
    const runEvidence = evidence.map((file) => ({ ...file }));
    const validationError = validateProjectProfile(runDraft.profile)
      ?? validateModeTask(runDraft, runMode)
      ?? validateModelSettings(runSettings);
    if (validationError) {
      setError(validationError);
      setStage("error");
      scrollPageTop();
      runLock.current = false;
      return;
    }

    workflowExecution.current = null;
    setWorkflowSteps([]);
    setExecutionKind("single");
    setError("");
    setStage("validating");
    setRecord(null);
    scrollPageTop();

    let auditReport: Record<string, unknown> | undefined;
    const shouldInspect = Boolean(
      runProject.siteUrl && runProject.allowNetworkEvidence && INSPECT_MODES.has(runModeId),
    );

    try {
      if (shouldInspect) {
        setStage("collecting");
        auditReport = await inspectSite(runProject, runSettings, runMaxPages);
      }

      setStage("analyzing");
      const result = await analyzeMode({
        mode: runModeId,
        project: runProject,
        settings: runSettings,
        evidence: runEvidence,
        auditReport,
      });
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
      const saved = saveRun(nextRecord);
      setRecord(nextRecord);
      setRuns(saved.runs);
      if (!saved.persisted) {
        setError("报告已生成，但浏览器存储空间不足；刷新页面后该记录将不保留。");
      }
      setStage("complete");
      setApiConnected(true);
      scrollPageTop();
    } catch (runError) {
      const message = runError instanceof Error ? runError.message : "运行失败，请稍后重试。";
      setError(message);
      setStage("error");
      scrollPageTop();
    } finally {
      runLock.current = false;
      setExecutionKind(null);
    }
  };

  const runWorkflow = async () => {
    if (runLock.current) return;
    runLock.current = true;
    const runDraft = cloneWorkspaceDraft(workspaceDraft);
    const auditProject = buildAnalysisProject(runDraft, "audit");
    const recoveryProject = buildAnalysisProject(runDraft, "recover");
    const reviewProject = buildAnalysisProject(runDraft, "review");
    const summaryProject = {
      ...auditProject,
      objective: runDraft.profile.primaryGoal,
    };
    const runSettings = { ...settings };
    const runEvidence = evidence.map((file) => ({ ...file }));
    const runMaxPages = maxPages;
    const validationError = validateProjectProfile(runDraft.profile)
      ?? validateModelSettings(runSettings);
    if (validationError) {
      setError(validationError);
      setStage("error");
      scrollPageTop();
      runLock.current = false;
      return;
    }

    const signature = currentWorkflowSignature;
    const existing = workflowExecution.current;
    const canResume = Boolean(
      existing &&
      existing.signature === signature &&
      existing.steps.some((step) => step.status === "error"),
    );
    const execution: WorkflowExecution = canResume && existing
      ? {
          ...existing,
          steps: existing.steps.map((step) =>
            step.status === "error"
              ? { mode: step.mode, status: "pending" }
              : { ...step },
          ),
        }
      : {
          signature,
          startedAt: new Date().toISOString(),
          inspectionComplete: false,
          steps: buildWorkflowPlan(recoveryProject, runEvidence, reviewProject),
        };

    const publishSteps = (steps: WorkflowStep[]) => {
      execution.steps = steps;
      workflowExecution.current = execution;
      setWorkflowSteps(steps.map((step) => ({ ...step })));
    };

    publishSteps(execution.steps);
    setExecutionKind("workflow");
    setError("");
    setRecord(null);
    setStage("validating");
    scrollPageTop();

    try {
      const shouldInspect = Boolean(
        auditProject.siteUrl && auditProject.allowNetworkEvidence,
      );
      if (!execution.inspectionComplete) {
        if (shouldInspect) {
          const wasUnavailable = inspectionUnavailable(execution.auditReport);
          setStage("collecting");
          try {
            execution.auditReport = await inspectSite(
              auditProject,
              runSettings,
              runMaxPages,
            );
          } catch (inspectionError) {
            execution.auditReport = {
              evidence_status: "unavailable",
              reason: inspectionError instanceof Error
                ? inspectionError.message
                : "公开 URL 证据暂时不可用。",
            };
          }
          execution.inspectionComplete = !inspectionUnavailable(execution.auditReport);
          if (wasUnavailable && execution.inspectionComplete) {
            execution.steps = execution.steps.map((item) =>
              item.status === "complete"
                ? { mode: item.mode, status: "pending" }
                : item,
            );
            publishSteps(execution.steps);
          }
        } else {
          execution.inspectionComplete = true;
        }
        workflowExecution.current = execution;
      }

      let steps = execution.steps;
      for (let index = 0; index < steps.length; index += 1) {
        const step = steps[index];
        if (step.status === "complete" || step.status === "skipped") continue;

        steps = steps.map((item, itemIndex) =>
          itemIndex === index
            ? { ...item, status: "running", reason: undefined }
            : item,
        );
        publishSteps(steps);
        setStage("analyzing");

        try {
          const stepProject = buildAnalysisProject(runDraft, step.mode);
          const result = await analyzeMode({
            mode: step.mode,
            project: stepProject,
            settings: runSettings,
            evidence: runEvidence,
            auditReport: execution.auditReport,
            workflowContext: buildWorkflowContext(steps),
          });
          steps = steps.map((item, itemIndex) =>
            itemIndex === index
              ? {
                  ...item,
                  status: "complete",
                  report: result.report,
                  createdAt: result.created_at || new Date().toISOString(),
                }
              : item,
          );
          publishSteps(steps);
          setApiConnected(true);
        } catch (stepError) {
          const message = stepError instanceof Error
            ? stepError.message
            : "该阶段运行失败。";
          steps = steps.map((item, itemIndex) =>
            itemIndex === index
              ? { ...item, status: "error", reason: message }
              : item,
          );
          publishSteps(steps);
          const label = MODES.find((item) => item.id === step.mode)?.label ?? step.mode;
          setError(`${label}阶段失败：${message}`);
          setStage("error");
          scrollPageTop();
          return;
        }
      }

      const completedAt = new Date().toISOString();
      const nextRecord: RunRecord = {
        id: crypto.randomUUID(),
        mode: "workflow",
        projectName: summaryProject.projectName,
        siteUrl: summaryProject.siteUrl,
        market: summaryProject.market,
        language: summaryProject.language,
        objective: runDraft.profile.primaryGoal,
        provider: runSettings.provider,
        model: runSettings.model,
        report: aggregateWorkflowMarkdown(summaryProject, steps),
        auditReport: execution.auditReport,
        evidence: runEvidence.map(({ name, type, size }) => ({ name, type, size })),
        createdAt: completedAt,
        workflow: {
          status: "complete",
          startedAt: execution.startedAt,
          completedAt,
          steps: steps.map(({ report: _report, ...step }) => step),
        },
      };
      const saved = saveRun(nextRecord);
      setRecord(nextRecord);
      setRuns(saved.runs);
      if (!saved.persisted) {
        setError("报告已生成，但浏览器存储空间不足；刷新页面后该记录将不保留。");
      }
      setStage("complete");
      setApiConnected(true);
      scrollPageTop();
    } catch (workflowError) {
      const message = workflowError instanceof Error
        ? workflowError.message
        : "自动流程无法完成。";
      setError(message);
      setStage("error");
      scrollPageTop();
    } finally {
      runLock.current = false;
      setExecutionKind(null);
    }
  };

  const resetRun = () => {
    setRecord(null);
    setStage("idle");
    setError("");
    setWorkflowSteps([]);
    workflowExecution.current = null;
  };

  return (
    <div className="app-frame">
      <header className="topbar">
        <Link className="brand-lockup" href="/" prefetch={false} aria-label="返回 Vibio SEO 首页">
          <Image src="/vibio-logo.png" alt="Vibio" width={37} height={37} priority />
          <div>
            <strong>Vibio SEO</strong>
            <span>Evidence Workspace</span>
          </div>
        </Link>
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

      <div className={`workspace-grid${!workspaceActive ? " workspace-grid--setup" : ""}`}>
        {workspaceActive && (
          <ModeRail modes={MODES} activeMode={modeId} onChange={changeMode} disabled={running} />
        )}

        <main className="main-workspace">
          {!hydrated ? (
            <div className="workspace-loading" role="status" aria-label="正在读取项目">
              <span className="workspace-loading__mark" />
              <strong>正在读取项目</strong>
            </div>
          ) : (
            <>
              {!showingProjectSetup && (
                <RunStatus
                  stage={stage}
                  analysisLabel={workflowRunning ? workflowAnalysisLabel : undefined}
                />
              )}
              {error && (
                <div className="error-banner" role="alert">
                  <TriangleAlert size={17} />
                  <span>{error}</span>
                  <button type="button" onClick={() => setError("")} aria-label="关闭错误提示">关闭</button>
                </div>
              )}

              {record ? (
                <ReportView record={record} onReset={resetRun} />
              ) : showingProjectSetup ? (
                <ProjectSetup
                  profile={workspaceDraft.profile}
                  sharedContext={workspaceDraft.sharedContext}
                  onChange={(profile) => {
                    setWorkspaceDraft((current) => ({ ...current, profile }));
                  }}
                  onSharedContextChange={(sharedContext) => {
                    setWorkspaceDraft((current) => ({ ...current, sharedContext }));
                  }}
                  onSubmit={() => {
                    const profileError = validateProjectProfile(workspaceDraft.profile);
                    if (profileError) {
                      setError(profileError);
                      setStage("error");
                      scrollPageTop();
                      return;
                    }
                    setProjectEstablished(true);
                    setEditingProject(false);
                    setError("");
                    setStage("idle");
                    scrollPageTop();
                  }}
                  disabled={running}
                  submitLabel={projectEstablished ? "保存项目设置" : "保存并进入工作台"}
                />
              ) : (
                <>
                  <WorkflowProgress steps={workflowSteps} />
                  <ModeTaskForm
                    mode={mode}
                    profile={workspaceDraft.profile}
                    draft={workspaceDraft.modes[modeId]}
                    onChange={(modeDraft) => {
                      setWorkspaceDraft((current) => ({
                        ...current,
                        modes: { ...current.modes, [modeId]: modeDraft },
                      }));
                    }}
                    onEditProject={() => {
                      setEditingProject(true);
                      setError("");
                      setStage("idle");
                      scrollPageTop();
                    }}
                    disabled={running}
                  />
                  <footer className="run-bar">
                    <div className="run-bar__contract">
                      <Sparkles size={17} aria-hidden="true" />
                      <div>
                        <span>{workflowSteps.length > 0 ? "自动流程" : "本次交付"}</span>
                        <strong>{workflowSteps.length > 0 ? workflowContract : mode.output}</strong>
                      </div>
                    </div>
                    <div className="run-actions">
                      <button
                        type="button"
                        className="run-button run-button--secondary"
                        onClick={() => void runAnalysis()}
                        disabled={running}
                      >
                        {singleRunning
                          ? <Sparkles size={18} className="pulse" />
                          : <Play size={18} fill="currentColor" />}
                        <span>{singleRunning ? "正在运行" : `运行${mode.label}`}</span>
                      </button>
                      <button
                        type="button"
                        className="run-button"
                        onClick={() => void runWorkflow()}
                        disabled={running}
                      >
                        {workflowRunning
                          ? <Sparkles size={18} className="pulse" />
                          : <Workflow size={18} />}
                        <span>
                          {workflowRunning
                            ? "自动流程运行中"
                            : workflowWillRetryInspection
                              ? "重试证据并继续"
                              : failedWorkflowStep && workflowCanResume
                              ? `从${MODES.find((item) => item.id === failedWorkflowStep.mode)?.label ?? failedWorkflowStep.mode}继续`
                              : failedWorkflowStep
                                ? "重新运行全流程"
                                : "自动跑全流程"}
                        </span>
                        {!running && <ArrowRight size={17} className="run-button__arrow" />}
                      </button>
                    </div>
                  </footer>
                </>
              )}
            </>
          )}
        </main>

        {workspaceActive && (
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
            siteUrl={workspaceDraft.profile.siteUrl}
            networkEnabled={workspaceDraft.profile.allowNetworkEvidence}
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
        )}
      </div>

      <HistoryDrawer
        open={historyOpen}
        runs={runs}
        modes={MODES}
        onClose={() => setHistoryOpen(false)}
        onSelect={(selected) => {
          setRecord(selected);
          if (selected.mode === "workflow") {
            setWorkflowSteps(selected.workflow?.steps ?? []);
          } else {
            setModeId(selected.mode);
            setWorkflowSteps([]);
          }
          workflowExecution.current = null;
          setExecutionKind(null);
          setStage("complete");
          setHistoryOpen(false);
          setError("");
          scrollPageTop();
        }}
        onClear={() => {
          clearRuns();
          setRuns([]);
        }}
      />
    </div>
  );
}
