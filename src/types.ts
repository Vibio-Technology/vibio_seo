export type ModeId =
  | "plan"
  | "audit"
  | "fix"
  | "keyword"
  | "write"
  | "link"
  | "review"
  | "recover";

export type WorkspaceExecutionMode = "single" | "automation";

export type RunStage =
  | "idle"
  | "validating"
  | "collecting"
  | "analyzing"
  | "complete"
  | "error";

export type ModeTaskFieldId = "objective" | "details" | "scope" | "timing";

export interface ModeTaskFieldDefinition {
  label: string;
  placeholder: string;
  required?: boolean;
  rows?: number;
}

export interface ModeTaskDefinition {
  objective: ModeTaskFieldDefinition;
  details: ModeTaskFieldDefinition;
  scope?: ModeTaskFieldDefinition;
  timing?: ModeTaskFieldDefinition;
}

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
  task: ModeTaskDefinition;
}

export interface ProjectProfile {
  projectName: string;
  siteUrl: string;
  market: string;
  language: string;
  conversion: string;
  primaryGoal: string;
  audience: string;
  businessModel: string;
  capacity: string;
  allowNetworkEvidence: boolean;
  allowStateDraft: boolean;
}

export interface ModeDraft {
  objective: string;
  details: string;
  scope: string;
  timing: string;
}

export type ModeDrafts = Record<ModeId, ModeDraft>;

export interface WorkspaceDraftV2 {
  schemaVersion: 2;
  profile: ProjectProfile;
  modes: ModeDrafts;
  sharedContext: string;
}

/** Flat, provider-facing project payload assembled for one analysis mode. */
export interface ProjectInput extends ProjectProfile {
  objective: string;
  scope: string;
  details: string;
  decisionWindow: string;
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

export type WorkflowStepStatus =
  | "pending"
  | "running"
  | "complete"
  | "waiting"
  | "skipped"
  | "error";

export interface WorkflowStep {
  mode: ModeId;
  status: WorkflowStepStatus;
  report?: string;
  reason?: string;
  createdAt?: string;
  inputModes?: ModeId[];
}

export type WorkflowStepState = WorkflowStep;

export interface WorkflowRunSummary {
  status: "complete" | "partial";
  startedAt: string;
  completedAt?: string;
  steps: WorkflowStep[];
}

export interface WorkflowExecutionSnapshot {
  schemaVersion: 1;
  signature: string;
  coreSignature: string;
  startedAt: string;
  inspectionComplete: boolean;
  maxPages: number;
  auditReport?: Record<string, unknown>;
  steps: WorkflowStep[];
  recordId?: string;
}

export interface WorkflowContextReport {
  mode: ModeId;
  artifactKind: WorkflowArtifactKind;
  report: string;
  truncated: boolean;
  createdAt?: string;
}

export type WorkflowArtifactKind =
  | "execution_plan"
  | "audit_findings"
  | "fix_contract"
  | "query_map"
  | "publish_package"
  | "link_plan"
  | "review_decision"
  | "incident_assessment";

export interface WorkflowContext {
  schemaVersion: "vibio-web.workflow-context.v1";
  completedReports: WorkflowContextReport[];
}

export interface ApiErrorPayload {
  detail?: string | { message?: string } | Array<{ msg?: string }>;
  message?: string;
}
