export type ModeId =
  | "plan"
  | "audit"
  | "fix"
  | "keyword"
  | "write"
  | "link"
  | "review"
  | "recover";

export type RunStage =
  | "idle"
  | "validating"
  | "collecting"
  | "analyzing"
  | "complete"
  | "error";

export interface ModeDefinition {
  id: ModeId;
  code: string;
  label: string;
  title: string;
  description: string;
  detailLabel: string;
  detailPlaceholder: string;
  evidenceHint: string;
  output: string;
  accent: string;
}

export interface ProjectInput {
  projectName: string;
  siteUrl: string;
  market: string;
  language: string;
  conversion: string;
  audience: string;
  businessModel: string;
  objective: string;
  scope: string;
  details: string;
  capacity: string;
  decisionWindow: string;
  allowNetworkEvidence: boolean;
  allowStateDraft: boolean;
}

export interface EvidenceFile {
  id: string;
  name: string;
  type: string;
  size: number;
  content: string;
}

export interface EvidenceSummary {
  name: string;
  type: string;
  size: number;
}

export interface ProviderModel {
  id: string;
  label: string;
}

export interface ProviderDefinition {
  id: string;
  label: string;
  short_label?: string;
  description: string;
  docs_url?: string;
  models: ProviderModel[];
  default_model: string;
}

export interface ModelSettings {
  provider: string;
  model: string;
  apiKey: string;
}

export interface InspectResponse {
  report: Record<string, unknown>;
  markdown: string;
}

export interface AnalysisResponse {
  report: string;
  provider: string;
  model: string;
  created_at: string;
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

export interface RunRecord {
  id: string;
  mode: ModeId | "workflow";
  projectName: string;
  siteUrl: string;
  market: string;
  language: string;
  objective: string;
  provider: string;
  model: string;
  report: string;
  auditReport?: Record<string, unknown>;
  evidence: EvidenceSummary[];
  createdAt: string;
  workflow?: WorkflowRunSummary;
}

export type WorkflowStepStatus = "pending" | "running" | "complete" | "skipped" | "error";

export interface WorkflowStep {
  mode: ModeId;
  status: WorkflowStepStatus;
  report?: string;
  reason?: string;
  createdAt?: string;
}

export type WorkflowStepState = WorkflowStep;

export interface WorkflowRunSummary {
  status: "complete" | "partial";
  startedAt: string;
  completedAt?: string;
  steps: WorkflowStep[];
}

export interface WorkflowContextReport {
  mode: ModeId;
  report: string;
  truncated: boolean;
  createdAt?: string;
}

export interface WorkflowContext {
  schemaVersion: "vibio-web.workflow-context.v1";
  completedReports: WorkflowContextReport[];
}

export interface ApiErrorPayload {
  detail?: string | { message?: string } | Array<{ msg?: string }>;
  message?: string;
}
