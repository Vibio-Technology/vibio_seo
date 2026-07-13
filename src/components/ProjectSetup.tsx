"use client";

import {
  ArrowRight,
  BriefcaseBusiness,
  Check,
  Globe2,
  SlidersHorizontal,
  Target,
  UsersRound,
} from "lucide-react";
import { useId, type FormEvent } from "react";
import type { ProjectProfile } from "../types";

export interface ProjectSetupProps {
  profile: ProjectProfile;
  onChange: (profile: ProjectProfile) => void;
  sharedContext?: string;
  onSharedContextChange?: (value: string) => void;
  onSubmit?: () => void;
  disabled?: boolean;
  submitLabel?: string;
}

function projectNameFromUrl(value: string): string {
  const candidate = value.trim();
  if (!candidate) return "";
  try {
    const url = new URL(candidate.includes("://") ? candidate : `https://${candidate}`);
    return url.hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
}

export function ProjectSetup({
  profile,
  onChange,
  sharedContext = "",
  onSharedContextChange,
  onSubmit,
  disabled = false,
  submitLabel = "保存并进入工作台",
}: ProjectSetupProps) {
  const headingId = useId();
  const update = <K extends keyof ProjectProfile>(key: K, value: ProjectProfile[K]) => {
    onChange({ ...profile, [key]: value });
  };
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit?.();
  };

  return (
    <form className="project-setup project-form" aria-labelledby={headingId} onSubmit={handleSubmit}>
      <header className="project-setup__intro mode-intro">
        <div className="mode-intro__index mode-intro__index--cyan">
          <Globe2 size={20} aria-hidden="true" />
        </div>
        <div>
          <span className="eyebrow">PROJECT SETUP</span>
          <h1 id={headingId}>建立项目档案</h1>
          <p>一份项目档案，连接后续所有 SEO 任务。</p>
        </div>
      </header>

      <section className="form-section" aria-labelledby={`${headingId}-core`}>
        <div className="form-section__title">
          <Target size={17} aria-hidden="true" />
          <h2 id={`${headingId}-core`}>核心信息</h2>
          <span>01</span>
        </div>
        <div className="form-grid form-grid--two">
          <label className="field">
            <span>项目名称 *</span>
            <input
              value={profile.projectName}
              onChange={(event) => update("projectName", event.target.value)}
              placeholder="例如：Vibio 德国站"
              autoComplete="organization"
              required
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>站点 URL</span>
            <input
              type="url"
              value={profile.siteUrl}
              onChange={(event) => update("siteUrl", event.target.value)}
              onBlur={() => {
                if (!profile.projectName.trim()) {
                  const inferred = projectNameFromUrl(profile.siteUrl);
                  if (inferred) update("projectName", inferred);
                }
              }}
              placeholder="https://example.com"
              autoComplete="url"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>目标国家 / 地区 *</span>
            <input
              value={profile.market}
              onChange={(event) => update("market", event.target.value)}
              placeholder="例如：德国"
              required
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>目标语言 *</span>
            <input
              value={profile.language}
              onChange={(event) => update("language", event.target.value)}
              placeholder="例如：de-DE"
              required
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>主要合格转化 *</span>
            <input
              value={profile.conversion}
              onChange={(event) => update("conversion", event.target.value)}
              placeholder="例如：通过技术评审的 RFQ"
              required
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>项目主要目标 *</span>
            <input
              value={profile.primaryGoal}
              onChange={(event) => update("primaryGoal", event.target.value)}
              placeholder="例如：找到阻碍询盘增长的 SEO 瓶颈"
              required
              disabled={disabled}
            />
          </label>
        </div>
      </section>

      <details className="project-setup__advanced form-section">
        <summary className="advanced-summary">
          <SlidersHorizontal size={17} aria-hidden="true" />
          <span>更多项目设置</span>
        </summary>
        <div className="form-grid form-grid--two project-setup__advanced-grid">
          <label className="field">
            <span><BriefcaseBusiness size={15} aria-hidden="true" />业务与产品</span>
            <input
              value={profile.businessModel}
              onChange={(event) => update("businessModel", event.target.value)}
              placeholder="商业模式、核心产品或服务"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span><UsersRound size={15} aria-hidden="true" />目标买家</span>
            <input
              value={profile.audience}
              onChange={(event) => update("audience", event.target.value)}
              placeholder="角色、公司类型、采购阶段"
              disabled={disabled}
            />
          </label>
          <label className="field">
            <span>执行产能 / 负责人</span>
            <input
              value={profile.capacity}
              onChange={(event) => update("capacity", event.target.value)}
              placeholder="例如：SEO 1 人，开发每周 2 天"
              disabled={disabled}
            />
          </label>
        </div>
        {onSharedContextChange && (
          <label className="field project-setup__context">
            <span>所有任务共享的背景</span>
            <textarea
              rows={4}
              value={sharedContext}
              onChange={(event) => onSharedContextChange(event.target.value)}
              placeholder="例如：历史决策、现有数据限制、品牌边界或所有任务都需要知道的上下文"
              disabled={disabled}
            />
          </label>
        )}
        <div className="permission-row project-setup__permissions">
          <label className="check-control">
            <input
              type="checkbox"
              checked={profile.allowNetworkEvidence}
              onChange={(event) => update("allowNetworkEvidence", event.target.checked)}
              disabled={disabled}
            />
            <span className="check-control__box"><Check size={13} /></span>
            <span>读取公开 URL 证据</span>
          </label>
          <label className="check-control">
            <input
              type="checkbox"
              checked={profile.allowStateDraft}
              onChange={(event) => update("allowStateDraft", event.target.checked)}
              disabled={disabled}
            />
            <span className="check-control__box"><Check size={13} /></span>
            <span>生成项目状态草稿</span>
          </label>
        </div>
      </details>

      {onSubmit && (
        <div className="project-setup__actions">
          <button type="submit" className="run-button" disabled={disabled}>
            <Check size={18} aria-hidden="true" />
            <span>{submitLabel}</span>
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </div>
      )}
    </form>
  );
}
