"use client";

import { Globe2, PencilLine, SlidersHorizontal, Target } from "lucide-react";
import { useId } from "react";
import type { ModeDefinition, ModeDraft, ModeId, ProjectProfile } from "../types";
import { MODES } from "../data";

export interface ModeTaskFormProps {
  mode: ModeDefinition;
  profile: ProjectProfile;
  draft: ModeDraft;
  onChange: (draft: ModeDraft) => void;
  onEditProject?: () => void;
  inheritedModes?: ModeId[];
  disabled?: boolean;
}

export function ModeTaskForm({
  mode,
  profile,
  draft,
  onChange,
  onEditProject,
  inheritedModes = [],
  disabled = false,
}: ModeTaskFormProps) {
  const headingId = useId();
  const taskHeadingId = `${headingId}-task`;
  const update = <K extends keyof ModeDraft>(key: K, value: ModeDraft[K]) => {
    onChange({ ...draft, [key]: value });
  };
  const objectivePlaceholder = profile.primaryGoal.trim()
    ? `默认：${profile.primaryGoal.trim()}`
    : mode.task.objective.placeholder;
  const inherited = inheritedModes.length > 0;
  const secondaryFields = ["details", "scope", "timing"] as const;
  const requiredFields = secondaryFields.filter(
    (field) => !inherited && mode.task[field]?.required,
  );
  const optionalFields = secondaryFields.filter((field) => {
    const definition = mode.task[field];
    return definition && (inherited || !definition.required);
  });

  const fieldControl = (field: typeof secondaryFields[number]) => {
    const definition = mode.task[field];
    if (!definition) return null;
    const required = Boolean(definition.required && !inherited);
    const label = `${definition.label}${required ? " *" : ""}`;
    if (field === "details") {
      return (
        <label className="field" key={field}>
          <span>{label}</span>
          <textarea
            rows={definition.rows ?? 4}
            value={draft[field]}
            onChange={(event) => update(field, event.target.value)}
            placeholder={definition.placeholder}
            required={required}
            disabled={disabled}
          />
        </label>
      );
    }
    return (
      <label className="field" key={field}>
        <span>{label}</span>
        <input
          value={draft[field]}
          onChange={(event) => update(field, event.target.value)}
          placeholder={definition.placeholder}
          required={required}
          disabled={disabled}
        />
      </label>
    );
  };

  return (
    <div className="project-form mode-task-form">
      <section className="project-summary" aria-label="当前项目">
        <div className="project-summary__identity">
          <Globe2 size={18} aria-hidden="true" />
          <div>
            <span className="eyebrow">当前项目</span>
            <strong>{profile.projectName || "未命名项目"}</strong>
            {profile.siteUrl && <span>{profile.siteUrl}</span>}
          </div>
        </div>
        <dl className="project-summary__facts">
          <div>
            <dt>市场</dt>
            <dd>{profile.market || "待设置"}</dd>
          </div>
          <div>
            <dt>语言</dt>
            <dd>{profile.language || "待设置"}</dd>
          </div>
          <div>
            <dt>合格转化</dt>
            <dd>{profile.conversion || "待设置"}</dd>
          </div>
        </dl>
        {onEditProject && (
          <button
            type="button"
            className="icon-button project-summary__edit"
            onClick={onEditProject}
            disabled={disabled}
          >
            <PencilLine size={16} aria-hidden="true" />
            <span>编辑项目</span>
          </button>
        )}
      </section>

      {inheritedModes.length > 0 && (
        <div className="handoff-banner" role="status">
          <span className="handoff-banner__label">自动继承</span>
          <strong>
            {inheritedModes.map((inputMode) =>
              MODES.find((item) => item.id === inputMode)?.label ?? inputMode
            ).join("、")}
          </strong>
          <span>上一阶段结果会作为只读上下文传入本次分析，无需粘贴，也不会覆盖当前草稿。</span>
        </div>
      )}

      <header className="mode-intro">
        <div className={`mode-intro__index mode-intro__index--${mode.accent}`}>{mode.code}</div>
        <div>
          <span className="eyebrow">{mode.label} / {mode.id.toUpperCase()}</span>
          <h1 id={headingId}>{mode.title}</h1>
          <p>{mode.description}</p>
        </div>
      </header>

      <section className="form-section mode-task-form__primary" aria-labelledby={taskHeadingId}>
        <div className="form-section__title">
          <Target size={17} aria-hidden="true" />
          <h2 id={taskHeadingId}>本次任务</h2>
          <span>01</span>
        </div>
        <label className="field mode-task-form__objective">
          <span>
            {mode.task.objective.label}
            {mode.task.objective.required && !inherited ? " *" : ""}
          </span>
          <textarea
            rows={mode.task.objective.rows ?? 3}
            value={draft.objective}
            onChange={(event) => update("objective", event.target.value)}
            placeholder={objectivePlaceholder}
            required={Boolean(mode.task.objective.required && !inherited)}
            disabled={disabled}
          />
        </label>
        {requiredFields.length > 0 && (
          <div className={requiredFields.length > 1 ? "form-grid form-grid--two form-grid--secondary" : "mode-task-form__required"}>
            {requiredFields.map(fieldControl)}
          </div>
        )}
      </section>

      {optionalFields.length > 0 && (
        <details className="form-section mode-task-form__advanced">
          <summary className="advanced-summary">
            <SlidersHorizontal size={17} aria-hidden="true" />
            <span>补充范围与约束</span>
          </summary>
          <div className="mode-task-form__advanced-fields">
            {optionalFields.map(fieldControl)}
          </div>
        </details>
      )}
    </div>
  );
}
