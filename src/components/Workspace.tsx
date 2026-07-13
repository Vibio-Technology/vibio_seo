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
  DEFAULT_AUTOMATION_CONFIG,
  buildAutomationGatingProject,
  buildAutomationPlan,
  buildAutomationProject,
  getAutomationEvidenceAvailability,
  selectAutomationEvidence,
  type AutomationConfig,
} from "../automation";
import {
  clearActiveWorkflow,
  clearRuns,
  loadActiveWorkflow,
  loadAutomationConfig,
  loadModelSettings,
  loadRuns,
  loadWorkspaceDraft,
  saveAutomationConfig,
  saveActiveWorkflow,
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
  WorkspaceExecutionMode,
  WorkspaceDraftV2,
  WorkflowExecutionSnapshot,
  WorkflowStep,
} from "../types";
import {
  aggregateWorkflowMarkdown,
  buildWorkflowContextForMode,
} from "../workflow";
import { buildAnalysisProject } from "../workspace-draft";
import { AutomationWorkspace } from "./AutomationWorkspace";
import { EvidencePanel } from "./EvidencePanel";
import { HistoryDrawer } from "./HistoryDrawer";
import { ModeTaskForm } from "./ModeTaskForm";
import { ModeRail } from "./ModeRail";
import { ProjectSetup } from "./ProjectSetup";
import { ProviderPanel } from "./ProviderPanel";
import { ReportView } from "./ReportView";
import { RunStatus } from "./RunStatus";

const DEFAULT_SETTINGS: ModelSettings = {
  provider: FALLBACK_PROVIDERS[0].id,
  model: FALLBACK_PROVIDERS[0].default_model,
  apiKey: "",
};

const INSPECT_MODES = new Set<ModeId>(["audit", "fix", "review", "recover", "plan", "link"]);

const SINGLE_NEXT_ACTIONS: Partial<Record<ModeId, {
  mode: ModeId;
  label: string;
  description: string;
}>> = {
  plan: {
    mode: "audit",
    label: "按此计划开始审计",
    description: "计划结果将作为审计的只读上下文，自动限定检查目标与证据缺口。",
  },
  recover: {
    mode: "audit",
    label: "继续定向审计",
    description: "恢复诊断将自动传给审计，用于验证根因和受影响范围。",
  },
  audit: {
    mode: "fix",
    label: "根据审计生成修复",
    description: "审计发现、证据边界和复验方式将自动传给修复，不覆盖修复草稿。",
  },
  keyword: {
    mode: "write",
    label: "按查询映射生成内容",
    description: "关键词与页面映射将自动传给内容阶段。",
  },
  write: {
    mode: "link",
    label: "继续规划发现与链接",
    description: "页面成稿和内链计划将自动传给链接阶段。",
  },
};

type ExecutionKind = "single" | "workflow";

type WorkflowExecution = WorkflowExecutionSnapshot;

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

function workflowCoreSignature(
  draft: WorkspaceDraftV2,
  settings: ModelSettings,
  maxPages: number,
  automationConfig: AutomationConfig,
): string {
  return JSON.stringify({
    draft,
    provider: settings.provider,
    model: settings.model,
    maxPages,
    automationConfig,
  });
}

function workflowInputSignature(
  draft: WorkspaceDraftV2,
  settings: ModelSettings,
  evidence: EvidenceFile[],
  maxPages: number,
  automationConfig: AutomationConfig,
): string {
  const selectedEvidence = selectAutomationEvidence(automationConfig, evidence);
  return JSON.stringify({
    core: workflowCoreSignature(draft, settings, maxPages, automationConfig),
    evidence: selectedEvidence.map(({ id: _id, ...file }) => file),
  });
}

function inspectionInputSignature(project: ProjectInput, maxPages: number): string {
  return JSON.stringify({
    siteUrl: project.siteUrl.trim().replace(/\/$/, ""),
    allowNetworkEvidence: project.allowNetworkEvidence,
    maxPages,
  });
}

function runMatchesProfile(record: RunRecord, profile: ProjectProfile): boolean {
  return (
    record.projectName.trim() === profile.projectName.trim() &&
    record.siteUrl.trim().replace(/\/$/, "") === profile.siteUrl.trim().replace(/\/$/, "") &&
    record.market.trim() === profile.market.trim() &&
    record.language.trim() === profile.language.trim()
  );
}

function inspectionUnavailable(report: Record<string, unknown> | undefined): boolean {
  return report?.evidence_status === "unavailable";
}

const ANALYSIS_CONNECTION_ERROR =
  "分析连接中断，服务端未确认是否完成。输入已保留；请先检查模型用量，再决定是否重新运行，重复提交可能再次计费。";
const ANALYSIS_TIMEOUT_ERROR =
  "模型在约 5 分钟的运行窗口内未完成。输入已保留；请重新运行，或改用响应更快的模型。";

type AnalysisStreamOutcome =
  | { result: AnalysisResponse }
  | { error: { status: number; detail: string } };

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function parseAnalysisStreamLine(
  line: string,
  accepted: boolean,
): { accepted: boolean; outcome?: AnalysisStreamOutcome } {
  const event = JSON.parse(line) as unknown;
  if (!isRecord(event) || typeof event.type !== "string") {
    throw new Error("invalid stream event");
  }
  if (event.type === "accepted") return { accepted: true };
  if (event.type === "heartbeat" && accepted) return { accepted };
  if (event.type === "complete" && accepted && isRecord(event.result)) {
    const result = event.result;
    if (
      typeof result.report === "string" &&
      typeof result.provider === "string" &&
      typeof result.model === "string" &&
      typeof result.created_at === "string"
    ) {
      return { accepted, outcome: { result: result as unknown as AnalysisResponse } };
    }
  }
  if (
    event.type === "error" &&
    accepted &&
    typeof event.status === "number" &&
    typeof event.detail === "string"
  ) {
    return { accepted, outcome: { error: { status: event.status, detail: event.detail } } };
  }
  throw new Error("invalid stream event");
}

async function readAnalysisStream(response: Response): Promise<AnalysisStreamOutcome> {
  if (!response.body) throw new Error(ANALYSIS_CONNECTION_ERROR);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let accepted = false;

  const readLines = (): AnalysisStreamOutcome | undefined => {
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) {
        const parsed = parseAnalysisStreamLine(line, accepted);
        accepted = parsed.accepted;
        if (parsed.outcome) return parsed.outcome;
      }
      newline = buffer.indexOf("\n");
    }
    return undefined;
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const outcome = readLines();
      if (outcome) return outcome;
    }
    buffer += decoder.decode();
    const outcome = readLines();
    if (outcome) return outcome;
    if (buffer.trim()) {
      const parsed = parseAnalysisStreamLine(buffer.trim(), accepted);
      if (parsed.outcome) return parsed.outcome;
    }
  } catch {
    try {
      await reader.cancel("invalid or interrupted analysis stream");
    } catch {
      // The connection may already be closed.
    }
    throw new Error(ANALYSIS_CONNECTION_ERROR);
  } finally {
    reader.releaseLock();
  }
  throw new Error(ANALYSIS_CONNECTION_ERROR);
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
  signal?: AbortSignal,
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
    signal,
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
  signal,
}: {
  mode: ModeId;
  project: ProjectInput;
  settings: ModelSettings;
  evidence: EvidenceFile[];
  auditReport?: Record<string, unknown>;
  workflowContext?: unknown;
  signal?: AbortSignal;
}): Promise<AnalysisResponse> {
  let response: Response;
  try {
    response = await fetch("/api/analyze/stream", {
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
      signal,
    });
  } catch {
    throw new Error(ANALYSIS_CONNECTION_ERROR);
  }
  if (!response.ok) {
    const message = await readApiError(response);
    throw new Error(
      response.status === 504 && message === "请求失败（504）"
        ? ANALYSIS_TIMEOUT_ERROR
        : message,
    );
  }
  const outcome = await readAnalysisStream(response);
  if ("error" in outcome) {
    throw new Error(outcome.error.status === 504 ? ANALYSIS_TIMEOUT_ERROR : outcome.error.detail);
  }
  return outcome.result;
}

export function Workspace() {
  const [modeId, setModeId] = useState<ModeId>("audit");
  const [workspaceExecutionMode, setWorkspaceExecutionMode] = useState<WorkspaceExecutionMode>("single");
  const [automationConfig, setAutomationConfig] = useState<AutomationConfig>(DEFAULT_AUTOMATION_CONFIG);
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
  const [singleChainSteps, setSingleChainSteps] = useState<WorkflowStep[]>([]);
  const [singleChainAuditReport, setSingleChainAuditReport] = useState<Record<string, unknown> | undefined>();
  const [singleChainAuditSignature, setSingleChainAuditSignature] = useState<string>();
  const [editingProject, setEditingProject] = useState(false);
  const [projectEstablished, setProjectEstablished] = useState(false);
  const runLock = useRef(false);
  const activeRunController = useRef<AbortController | null>(null);
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
  const singleInheritedModes = useMemo(
    () => buildWorkflowContextForMode(singleChainSteps, modeId).completedReports.map((item) => item.mode),
    [modeId, singleChainSteps],
  );
  const failedWorkflowStep = workflowSteps.find((step) => step.status === "error");
  const nextWorkflowStep = workflowSteps.find(
    (step) => step.status === "error" || step.status === "pending",
  );
  const currentWorkflowSignature = useMemo(
    () => workflowInputSignature(workspaceDraft, settings, evidence, maxPages, automationConfig),
    [automationConfig, evidence, maxPages, settings.model, settings.provider, workspaceDraft],
  );
  const currentWorkflowCoreSignature = useMemo(
    () => workflowCoreSignature(workspaceDraft, settings, maxPages, automationConfig),
    [automationConfig, maxPages, settings.model, settings.provider, workspaceDraft],
  );
  const automationGatingProject = useMemo(
    () => buildAutomationGatingProject(workspaceDraft, automationConfig),
    [automationConfig, workspaceDraft],
  );
  const automationReviewProject = useMemo(
    () => buildAutomationProject(workspaceDraft, "review", automationConfig),
    [automationConfig, workspaceDraft],
  );
  const automationPreviewSteps = useMemo(
    () => buildAutomationPlan(
      automationConfig,
      automationGatingProject,
      selectAutomationEvidence(automationConfig, evidence),
      automationReviewProject,
    ),
    [automationConfig, automationGatingProject, automationReviewProject, evidence],
  );
  const automationEvidenceAvailability = useMemo(
    () => getAutomationEvidenceAvailability(
      automationReviewProject,
      evidence,
    ),
    [automationReviewProject, evidence],
  );
  const readyWaitingModes = useMemo(
    () => new Set(
      automationPreviewSteps
        .filter((step) => step.status === "pending")
        .map((step) => step.mode),
    ),
    [automationPreviewSteps],
  );
  const waitingWorkflowStep = workflowSteps.find((step) => step.status === "waiting");
  const readyWaitingStep = waitingWorkflowStep && readyWaitingModes.has(waitingWorkflowStep.mode)
    ? waitingWorkflowStep
    : undefined;
  const currentExecution = workflowExecution.current;
  const workflowWaitingCanResume = Boolean(
    readyWaitingStep &&
    currentExecution?.coreSignature === currentWorkflowCoreSignature,
  );
  const workflowCanResume = Boolean(
    currentExecution && (
      currentExecution.signature === currentWorkflowSignature && (
        nextWorkflowStep || currentExecution.inspectionComplete === false
      ) || workflowWaitingCanResume
    ),
  );
  const workflowWillRetryInspection = Boolean(
    workflowCanResume &&
    currentExecution?.inspectionComplete === false &&
    automationConfig.evidenceSources.includes("site") &&
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
    const waiting = workflowSteps.filter((step) => step.status === "waiting").length;
    if (failedWorkflowStep) {
      const label = MODES.find((item) => item.id === failedWorkflowStep.mode)?.label;
      return workflowWillRetryInspection
        ? "URL 证据将重试 · 恢复后重算已完成阶段"
        : workflowCanResume
          ? `已完成 ${completed} 步 · 可从${label ?? failedWorkflowStep.mode}继续`
        : "输入已变化 · 将从头重新运行";
    }
    if (workflowWillRetryInspection) {
      return "公开站点证据未完成 · 可重试后重算受影响阶段";
    }
    if (readyWaitingStep && workflowWaitingCanResume) {
      const label = MODES.find((item) => item.id === readyWaitingStep.mode)?.label;
      return `已完成 ${completed} 步 · ${label ?? readyWaitingStep.mode}材料已就绪`;
    }
    if (nextWorkflowStep && workflowCanResume) {
      const label = MODES.find((item) => item.id === nextWorkflowStep.mode)?.label;
      return `已完成 ${completed} 步 · 下一步 ${label ?? nextWorkflowStep.mode}`;
    }
    if (nextWorkflowStep && workflowSteps.length > 0) {
      return "输入已变化 · 再次启动将从头运行";
    }
    return `已完成 ${completed} 步 · 条件跳过 ${skipped} 步 · 等待材料 ${waiting} 步`;
  }, [
    failedWorkflowStep,
    nextWorkflowStep,
    readyWaitingStep,
    workflowCanResume,
    workflowSteps,
    workflowWaitingCanResume,
    workflowWillRetryInspection,
  ]);
  const firstAutomationStep = automationPreviewSteps.find((step) => step.status === "pending");
  const automationActionMode = workflowCanResume
    ? nextWorkflowStep ?? readyWaitingStep
    : firstAutomationStep;
  const automationActionLabel = workflowRunning
    ? "自动流程运行中"
    : workflowWillRetryInspection
      ? "重试站点证据"
      : failedWorkflowStep && workflowCanResume
      ? `重试${MODES.find((item) => item.id === failedWorkflowStep.mode)?.label ?? failedWorkflowStep.mode}`
      : workflowCanResume && automationActionMode
        ? `继续到${MODES.find((item) => item.id === automationActionMode.mode)?.label ?? automationActionMode.mode}`
        : workflowSteps.length > 0 && nextWorkflowStep
          ? "按新输入重新开始"
        : automationConfig.advanceMode === "continuous"
          ? "启动连续分析"
          : `确认路线并开始${firstAutomationStep
            ? MODES.find((item) => item.id === firstAutomationStep.mode)?.label ?? firstAutomationStep.mode
            : "运行"}`;
  const automationContract = workflowSteps.length > 0
    ? workflowContract
    : `已编排 ${automationPreviewSteps.length} 个阶段 · ${automationConfig.advanceMode === "approval" ? "逐步确认" : "连续分析"}`;

  useEffect(() => {
    const storedDraft = loadWorkspaceDraft(EMPTY_WORKSPACE_DRAFT);
    const storedSettings = loadModelSettings(DEFAULT_SETTINGS);
    const storedAutomationConfig = loadAutomationConfig();
    const storedRuns = loadRuns();
    const storedWorkflow = loadActiveWorkflow();
    const profileComplete = projectProfileIsComplete(storedDraft.profile);
    setWorkspaceDraft(storedDraft);
    setProjectEstablished(profileComplete);
    setSettings(storedSettings);
    setAutomationConfig(storedAutomationConfig);
    setRuns(storedRuns);

    if (
      profileComplete &&
      storedWorkflow &&
      storedWorkflow.coreSignature === workflowCoreSignature(
        storedDraft,
        storedSettings,
        storedWorkflow.maxPages,
        storedAutomationConfig,
      )
    ) {
      const interrupted = storedWorkflow.steps.some((step) => step.status === "running");
      const restoredWorkflow: WorkflowExecution = {
        ...storedWorkflow,
        steps: storedWorkflow.steps.map((step) =>
          step.status === "running"
            ? {
                ...step,
                status: "error",
                reason: "页面刷新时该阶段仍在运行，服务端状态未知；重试可能重复计费。",
              }
            : step,
        ),
      };
      workflowExecution.current = restoredWorkflow;
      setWorkflowSteps(restoredWorkflow.steps);
      setWorkspaceExecutionMode("automation");
      setMaxPages(restoredWorkflow.maxPages);
      const restoredFailure = restoredWorkflow.steps.find((step) => step.status === "error");
      const partialRecord = restoredWorkflow.recordId
        ? storedRuns.find((run) => run.id === restoredWorkflow.recordId && run.mode === "workflow")
        : undefined;
      if (restoredFailure) {
        setError(interrupted
          ? "上次运行在页面刷新时中断。已保留之前的结果，请确认后重试当前阶段。"
          : restoredFailure.reason ?? "上次流程在当前阶段失败，可从该阶段继续。");
        setStage("error");
        saveActiveWorkflow(restoredWorkflow);
      } else if (partialRecord) {
        setRecord(partialRecord);
        setStage("complete");
      }
    } else if (storedWorkflow) {
      clearActiveWorkflow();
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveWorkspaceDraft(workspaceDraft);
  }, [hydrated, workspaceDraft]);

  useEffect(() => {
    if (hydrated) saveModelSettings(settings);
  }, [hydrated, settings]);

  useEffect(() => {
    if (hydrated) saveAutomationConfig(automationConfig);
  }, [automationConfig, hydrated]);

  useEffect(() => () => {
    activeRunController.current?.abort("workspace unmounted");
  }, []);

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

  const discardActiveWorkflow = () => {
    workflowExecution.current = null;
    clearActiveWorkflow();
  };

  const changeMode = (nextMode: ModeId) => {
    setWorkspaceExecutionMode("single");
    setModeId(nextMode);
    setRecord(null);
    setStage("idle");
    setError("");
    setWorkflowSteps([]);
    setSingleChainSteps([]);
    setSingleChainAuditReport(undefined);
    setSingleChainAuditSignature(undefined);
    discardActiveWorkflow();
  };

  const changeWorkspaceExecutionMode = (nextMode: WorkspaceExecutionMode) => {
    if (nextMode === workspaceExecutionMode) return;
    setWorkspaceExecutionMode(nextMode);
    setRecord(null);
    setStage("idle");
    setError("");
    setWorkflowSteps([]);
    setSingleChainSteps([]);
    setSingleChainAuditReport(undefined);
    setSingleChainAuditSignature(undefined);
    discardActiveWorkflow();
    scrollPageTop();
  };

  const resetAutomationFlow = () => {
    setRecord(null);
    setStage("idle");
    setError("");
    setWorkflowSteps([]);
    setSingleChainSteps([]);
    setSingleChainAuditReport(undefined);
    setSingleChainAuditSignature(undefined);
    discardActiveWorkflow();
    scrollPageTop();
  };

  const continueSingleChain = (source: RunRecord, nextMode: ModeId) => {
    const sourceMode = source.mode;
    if (sourceMode === "workflow") return;
    setSingleChainSteps((current) => {
      const sourceStep: WorkflowStep = {
        mode: sourceMode,
        status: "complete",
        report: source.report,
        createdAt: source.createdAt,
      };
      return [...current.filter((step) => step.mode !== sourceMode), sourceStep];
    });
    if (source.auditReport && runMatchesProfile(source, workspaceDraft.profile)) {
      setSingleChainAuditReport(source.auditReport);
      setSingleChainAuditSignature(inspectionInputSignature(
        buildAnalysisProject(workspaceDraft, sourceMode),
        maxPages,
      ));
    }
    setWorkspaceExecutionMode("single");
    setModeId(nextMode);
    setRecord(null);
    setStage("idle");
    setError("");
    setWorkflowSteps([]);
    discardActiveWorkflow();
    scrollPageTop();
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
    const inheritedContext = buildWorkflowContextForMode(singleChainSteps, runModeId);
    const currentInspectionSignature = inspectionInputSignature(runProject, runMaxPages);
    const validationError = validateProjectProfile(runDraft.profile)
      ?? (inheritedContext.completedReports.length > 0 ? null : validateModeTask(runDraft, runMode))
      ?? validateModelSettings(runSettings);
    if (validationError) {
      setError(validationError);
      setStage("error");
      scrollPageTop();
      runLock.current = false;
      return;
    }

    const controller = new AbortController();
    activeRunController.current = controller;

    discardActiveWorkflow();
    setWorkflowSteps([]);
    setExecutionKind("single");
    setError("");
    setStage("validating");
    setRecord(null);
    scrollPageTop();

    let auditReport: Record<string, unknown> | undefined =
      singleChainAuditSignature === currentInspectionSignature
        ? singleChainAuditReport
        : undefined;
    const shouldInspect = Boolean(
      (!auditReport || inspectionUnavailable(auditReport)) &&
      runProject.siteUrl &&
      runProject.allowNetworkEvidence &&
      INSPECT_MODES.has(runModeId),
    );

    try {
      if (shouldInspect) {
        setStage("collecting");
        auditReport = await inspectSite(runProject, runSettings, runMaxPages, controller.signal);
      }

      setStage("analyzing");
      const result = await analyzeMode({
        mode: runModeId,
        project: runProject,
        settings: runSettings,
        evidence: runEvidence,
        auditReport,
        workflowContext: inheritedContext.completedReports.length > 0
          ? inheritedContext
          : undefined,
        signal: controller.signal,
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
      setSingleChainSteps((current) => [
        ...current.filter((step) => step.mode !== runModeId),
        {
          mode: runModeId,
          status: "complete",
          report: result.report,
          createdAt,
          inputModes: inheritedContext.completedReports.map((item) => item.mode),
        },
      ]);
      if (auditReport) {
        setSingleChainAuditReport(auditReport);
        setSingleChainAuditSignature(currentInspectionSignature);
      }
      setRecord(nextRecord);
      setRuns(saved.runs);
      if (!saved.persisted) {
        setError("报告已生成，但浏览器存储空间不足；刷新页面后该记录将不保留。");
      }
      setStage("complete");
      setApiConnected(true);
      scrollPageTop();
    } catch (runError) {
      if (controller.signal.aborted) return;
      const message = runError instanceof Error ? runError.message : "运行失败，请稍后重试。";
      setError(message);
      setStage("error");
      scrollPageTop();
    } finally {
      if (activeRunController.current === controller) activeRunController.current = null;
      runLock.current = false;
      setExecutionKind(null);
    }
  };

  const runWorkflow = async () => {
    if (runLock.current) return;
    runLock.current = true;
    const runDraft = cloneWorkspaceDraft(workspaceDraft);
    const auditProject = buildAutomationProject(runDraft, "audit", automationConfig);
    const gatingProject = buildAutomationGatingProject(runDraft, automationConfig);
    const reviewProject = buildAutomationProject(runDraft, "review", automationConfig);
    const summaryProject = {
      ...auditProject,
      objective: automationConfig.objective.trim() || runDraft.profile.primaryGoal,
    };
    const runSettings = { ...settings };
    const runEvidence = selectAutomationEvidence(automationConfig, evidence)
      .map((file) => ({ ...file }));
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

    const controller = new AbortController();
    activeRunController.current = controller;

    const coreSignature = workflowCoreSignature(
      runDraft,
      runSettings,
      runMaxPages,
      automationConfig,
    );
    const signature = workflowInputSignature(
      runDraft,
      runSettings,
      runEvidence,
      runMaxPages,
      automationConfig,
    );
    const refreshedPlan = buildAutomationPlan(
      automationConfig,
      gatingProject,
      runEvidence,
      reviewProject,
    );
    const refreshedPendingModes = new Set(
      refreshedPlan
        .filter((step) => step.status === "pending")
        .map((step) => step.mode),
    );
    const existing = workflowExecution.current;
    const canResume = Boolean(
      existing && (
        existing.signature === signature && (
          existing.inspectionComplete === false ||
          existing.steps.some((step) => step.status === "error" || step.status === "pending")
        ) ||
        existing.coreSignature === coreSignature && existing.steps.some(
          (step) => step.status === "waiting" && refreshedPendingModes.has(step.mode),
        )
      ),
    );
    const execution: WorkflowExecution = canResume && existing
      ? {
          ...existing,
          signature,
          coreSignature,
          steps: existing.steps.map((step) =>
            step.status === "error"
              ? { ...step, status: "pending", reason: undefined }
              : step.status === "waiting" && refreshedPendingModes.has(step.mode)
                ? { ...step, status: "pending", reason: undefined }
              : { ...step },
          ),
        }
      : {
          schemaVersion: 1,
          signature,
          coreSignature,
          startedAt: new Date().toISOString(),
          inspectionComplete: false,
          maxPages: runMaxPages,
          steps: refreshedPlan,
        };

    const publishSteps = (steps: WorkflowStep[]) => {
      execution.steps = steps;
      workflowExecution.current = execution;
      saveActiveWorkflow(execution);
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
        automationConfig.evidenceSources.includes("site") &&
        execution.steps.some((step) => INSPECT_MODES.has(step.mode)) &&
        auditProject.siteUrl &&
        auditProject.allowNetworkEvidence,
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
              controller.signal,
            );
          } catch (inspectionError) {
            if (controller.signal.aborted) throw inspectionError;
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
        saveActiveWorkflow(execution);
      }

      let steps = execution.steps;
      for (let index = 0; index < steps.length; index += 1) {
        const step = steps[index];
        if (["complete", "skipped", "waiting"].includes(step.status)) continue;

        const workflowContext = buildWorkflowContextForMode(steps, step.mode);
        const inputModes = workflowContext.completedReports.map((item) => item.mode);

        steps = steps.map((item, itemIndex) =>
          itemIndex === index
            ? { ...item, status: "running", reason: undefined, inputModes }
            : item,
        );
        publishSteps(steps);
        setStage("analyzing");

        try {
          const stepProject = buildAutomationProject(runDraft, step.mode, automationConfig);
          const result = await analyzeMode({
            mode: step.mode,
            project: stepProject,
            settings: runSettings,
            evidence: runEvidence,
            auditReport: execution.auditReport,
            workflowContext: workflowContext.completedReports.length > 0
              ? workflowContext
              : undefined,
            signal: controller.signal,
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
          const hasNextStep = steps.slice(index + 1).some((item) => item.status === "pending");
          if (automationConfig.advanceMode === "approval" && hasNextStep) {
            setStage("idle");
            scrollPageTop();
            return;
          }
        } catch (stepError) {
          if (controller.signal.aborted) return;
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
        id: execution.recordId ?? crypto.randomUUID(),
        mode: "workflow",
        projectName: summaryProject.projectName,
        siteUrl: summaryProject.siteUrl,
        market: summaryProject.market,
        language: summaryProject.language,
        objective: summaryProject.objective,
        provider: runSettings.provider,
        model: runSettings.model,
        report: aggregateWorkflowMarkdown(summaryProject, steps),
        auditReport: execution.auditReport,
        evidence: runEvidence.map(({ name, type, size }) => ({ name, type, size })),
        createdAt: completedAt,
        workflow: {
          status: steps.some((step) => step.status === "waiting") || !execution.inspectionComplete
            ? "partial"
            : "complete",
          startedAt: execution.startedAt,
          completedAt,
          steps: steps.map(({ report: _report, ...step }) => step),
        },
      };
      execution.recordId = nextRecord.id;
      workflowExecution.current = execution;
      if (nextRecord.workflow?.status === "partial") {
        saveActiveWorkflow(execution);
      } else {
        clearActiveWorkflow();
      }
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
      if (controller.signal.aborted) return;
      const message = workflowError instanceof Error
        ? workflowError.message
        : "自动流程无法完成。";
      setError(message);
      setStage("error");
      scrollPageTop();
    } finally {
      if (activeRunController.current === controller) activeRunController.current = null;
      runLock.current = false;
      setExecutionKind(null);
    }
  };

  const resetRun = () => {
    setRecord(null);
    setStage("idle");
    setError("");
    setWorkflowSteps([]);
    setSingleChainSteps([]);
    setSingleChainAuditReport(undefined);
    setSingleChainAuditSignature(undefined);
    discardActiveWorkflow();
  };
  const nextSingleAction = record && record.mode !== "workflow" && runMatchesProfile(record, workspaceDraft.profile)
    ? SINGLE_NEXT_ACTIONS[record.mode]
    : undefined;
  const workflowRecordIsCurrent = Boolean(
    record?.mode === "workflow" &&
    record.workflow?.status === "partial" &&
    workflowExecution.current?.recordId === record.id,
  );
  const nextWorkflowAction = workflowRecordIsCurrent
    ? workflowWillRetryInspection
      ? {
          label: "重试站点证据",
          description: "公开 URL 证据未完成。重试成功后会重算已受影响的阶段。",
          onContinue: () => { void runWorkflow(); },
        }
      : waitingWorkflowStep
        ? {
            label: workflowWaitingCanResume
              ? `继续到${MODES.find((item) => item.id === waitingWorkflowStep.mode)?.label ?? waitingWorkflowStep.mode}`
              : "等待复盘材料",
            description: workflowWaitingCanResume
              ? "新材料已就绪，将保留已完成阶段，只运行等待中的复盘。"
              : "在右侧上传发布记录或 GSC、GA4、CRM 对比导出后即可继续。",
            onContinue: () => { void runWorkflow(); },
            disabled: !workflowWaitingCanResume,
          }
        : undefined
    : undefined;
  const reportNextAction = nextSingleAction && record && record.mode !== "workflow"
    ? {
        label: nextSingleAction.label,
        description: nextSingleAction.description,
        onContinue: () => continueSingleChain(record, nextSingleAction.mode),
      }
    : nextWorkflowAction;

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
          <button
            type="button"
            className="icon-button"
            onClick={() => setHistoryOpen(true)}
            disabled={running}
            aria-label="运行记录"
            title="运行记录"
          >
            <History size={17} />
            <span>运行记录</span>
            {runs.length > 0 && <span className="button-count">{runs.length}</span>}
          </button>
        </div>
      </header>

      <div className={`workspace-grid${!workspaceActive ? " workspace-grid--setup" : ""}`}>
        {workspaceActive && (
          <ModeRail
            modes={MODES}
            activeMode={modeId}
            onChange={changeMode}
            executionMode={workspaceExecutionMode}
            onExecutionModeChange={changeWorkspaceExecutionMode}
            disabled={running}
          />
        )}

        <main className="main-workspace" id="main-content">
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
                <ReportView
                  record={record}
                  onReset={resetRun}
                  nextAction={reportNextAction}
                />
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
                    if (editingProject) {
                      setWorkflowSteps([]);
                      setSingleChainSteps([]);
                      setSingleChainAuditReport(undefined);
                      setSingleChainAuditSignature(undefined);
                      discardActiveWorkflow();
                    }
                    setError("");
                    setStage("idle");
                    scrollPageTop();
                  }}
                  disabled={running}
                  submitLabel={projectEstablished ? "保存项目设置" : "保存并进入工作台"}
                />
              ) : workspaceExecutionMode === "automation" ? (
                <>
                  <AutomationWorkspace
                    profile={workspaceDraft.profile}
                    config={automationConfig}
                    onChange={setAutomationConfig}
                    previewSteps={automationPreviewSteps}
                    steps={workflowSteps}
                    evidenceAvailability={automationEvidenceAvailability}
                    onEditProject={() => {
                      setEditingProject(true);
                      setError("");
                      setStage("idle");
                      scrollPageTop();
                    }}
                    onResetFlow={resetAutomationFlow}
                    disabled={running}
                  />
                  <footer className="run-bar">
                    <div className="run-bar__contract">
                      <Workflow size={17} aria-hidden="true" />
                      <div>
                        <span>自动流程</span>
                        <strong>{automationContract}</strong>
                      </div>
                    </div>
                    <div className="run-actions run-actions--single">
                      <button
                        type="button"
                        className="run-button"
                        onClick={() => void runWorkflow()}
                        disabled={running || !firstAutomationStep && !workflowCanResume}
                      >
                        {workflowRunning
                          ? <Sparkles size={18} className="pulse" />
                          : <Workflow size={18} />}
                        <span>{automationActionLabel}</span>
                        {!running && <ArrowRight size={17} className="run-button__arrow" />}
                      </button>
                    </div>
                  </footer>
                </>
              ) : (
                <>
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
                    inheritedModes={singleInheritedModes}
                    disabled={running}
                  />
                  <footer className="run-bar">
                    <div className="run-bar__contract">
                      <Sparkles size={17} aria-hidden="true" />
                      <div>
                        <span>本次交付</span>
                        <strong>{mode.output}</strong>
                      </div>
                    </div>
                    <div className="run-actions run-actions--single">
                      <button
                        type="button"
                        className="run-button"
                        onClick={() => void runAnalysis()}
                        disabled={running}
                      >
                        {singleRunning
                          ? <Sparkles size={18} className="pulse" />
                          : <Play size={18} fill="currentColor" />}
                        <span>{singleRunning ? "正在运行" : `运行${mode.label}`}</span>
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
            mode={workspaceExecutionMode === "automation"
              ? MODES.find((item) => item.id === "audit") ?? mode
              : mode}
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
          setSingleChainSteps([]);
          setSingleChainAuditReport(undefined);
          setSingleChainAuditSignature(undefined);
          if (selected.mode === "workflow") {
            setWorkspaceExecutionMode("automation");
            setWorkflowSteps(selected.workflow?.steps ?? []);
          } else {
            setWorkspaceExecutionMode("single");
            setModeId(selected.mode);
            setWorkflowSteps([]);
          }
          discardActiveWorkflow();
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
