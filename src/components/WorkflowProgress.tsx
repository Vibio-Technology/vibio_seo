import {
  Check,
  CircleDashed,
  LoaderCircle,
  Minus,
  TriangleAlert,
} from "lucide-react";
import type { ComponentType } from "react";
import { MODES } from "../data";
import type { WorkflowStep } from "../types";

interface WorkflowProgressProps {
  steps: WorkflowStep[];
  compact?: boolean;
}

const STATUS_META: Record<
  WorkflowStep["status"],
  {
    label: string;
    Icon: ComponentType<{ size?: number; className?: string }>;
  }
> = {
  pending: { label: "待执行", Icon: CircleDashed },
  running: { label: "运行中", Icon: LoaderCircle },
  complete: { label: "已完成", Icon: Check },
  skipped: { label: "已跳过", Icon: Minus },
  error: { label: "失败", Icon: TriangleAlert },
};

export function WorkflowProgress({ steps, compact = false }: WorkflowProgressProps) {
  if (steps.length === 0) return null;

  const runningIndex = steps.findIndex((step) => step.status === "running");
  const errorIndex = steps.findIndex((step) => step.status === "error");
  const pendingIndex = steps.findIndex((step) => step.status === "pending");
  const currentPosition = runningIndex >= 0
    ? runningIndex + 1
    : errorIndex >= 0
      ? errorIndex + 1
      : pendingIndex >= 0
        ? pendingIndex
        : steps.length;

  return (
    <section
      className={`workflow-progress${compact ? " is-compact" : ""}`}
      aria-label="自动工作流进度"
    >
      <header className="workflow-progress__header">
        <div>
          <span className="eyebrow">自动工作流</span>
          <h2>能力链进度</h2>
        </div>
        <span className="workflow-progress__count" aria-live="polite">
          <strong>{currentPosition}</strong>
          <span>/ {steps.length}</span>
        </span>
      </header>

      <ol className="workflow-progress__list">
        {steps.map((step) => {
          const mode = MODES.find((item) => item.id === step.mode);
          const { Icon, label } = STATUS_META[step.status];

          return (
            <li
              className={`workflow-step workflow-step--${step.status}`}
              key={step.mode}
              aria-current={step.status === "running" ? "step" : undefined}
            >
              <span className="workflow-step__index" aria-hidden="true">
                {mode?.code ?? "--"}
              </span>
              <div className="workflow-step__body">
                <strong>{mode?.label ?? step.mode}</strong>
                <span>{mode?.title ?? "工作流步骤"}</span>
                {step.reason && <small>{step.reason}</small>}
              </div>
              <span className="workflow-step__state">
                <Icon
                  size={14}
                  className={step.status === "running" ? "spin" : undefined}
                />
                <span>{label}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
