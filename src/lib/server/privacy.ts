export const MAX_REQUEST_BYTES = 2 * 1024 * 1024;
export const MAX_PROJECT_BYTES = 24 * 1024;
export const MAX_EVIDENCE_BYTES = 96 * 1024;
export const MAX_AUDIT_REPORT_BYTES = 512 * 1024;
export const MAX_PROVIDER_RESPONSE_BYTES = 2 * 1024 * 1024;
export const MAX_API_KEY_LENGTH = 4096;
export const MAX_JSON_DEPTH = 32;
export const MAX_JSON_NODES = 20_000;

const EMAIL_RE = /(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])/i;
const CN_PHONE_RE = /(?<!\d)(?:\+?86[-\s]?)?1[3-9]\d{9}(?!\d)/;
const FORMATTED_PHONE_RE =
  /(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]\d{3,4}[\s.-]\d{3,4}(?!\w)/;
const CN_ID_RE = /(?<!\d)\d{17}[0-9Xx](?!\d)/;
const OPENAI_STYLE_KEY_RE = /(?<![A-Za-z0-9])[A-Za-z]{0,12}sk-[A-Za-z0-9_-]{16,}/;
const JWT_RE = /(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/;
const CREDENTIAL_ASSIGNMENT_RE =
  /(?:api[_ -]?key|access[_ -]?token|secret|password|authorization)\s*[:=]\s*[^\s,;]{6,}/i;

const SENSITIVE_FIELD_NAMES = new Set([
  "api_key",
  "apikey",
  "access_token",
  "refresh_token",
  "authorization",
  "password",
  "passwd",
  "secret",
  "client_secret",
  "private_key",
  "cookie",
  "set_cookie",
]);

export class PublicHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(detail);
    this.name = "PublicHttpError";
  }
}

export class PrivacyViolation extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PrivacyViolation";
  }
}

function jsonBytes(value: unknown, label: string): number {
  let serialized: string | undefined;
  try {
    serialized = JSON.stringify(value);
  } catch {
    throw new PrivacyViolation(`${label}必须是有效的 JSON 数据。`);
  }
  if (serialized === undefined) {
    throw new PrivacyViolation(`${label}必须是有效的 JSON 数据。`);
  }
  return new TextEncoder().encode(serialized).byteLength;
}

export function ensureJsonSize(value: unknown, label: string, maxBytes: number): void {
  if (jsonBytes(value, label) > maxBytes) {
    throw new PrivacyViolation(`${label}超过 ${maxBytes} 字节限制。`);
  }
}

function normalizedFieldName(value: string): string {
  return value
    .trim()
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function isSensitiveField(name: string): boolean {
  const normalized = normalizedFieldName(name);
  return (
    SENSITIVE_FIELD_NAMES.has(normalized) ||
    ["_api_key", "_access_token", "_refresh_token", "_client_secret", "_password"].some(
      (suffix) => normalized.endsWith(suffix),
    )
  );
}

function scanText(value: string, location: string): void {
  if (EMAIL_RE.test(value)) {
    throw new PrivacyViolation(`${location}包含电子邮箱；请先删除或不可逆脱敏。`);
  }
  if (CN_PHONE_RE.test(value) || FORMATTED_PHONE_RE.test(value)) {
    throw new PrivacyViolation(`${location}包含电话号码；请先删除或不可逆脱敏。`);
  }
  if (CN_ID_RE.test(value)) {
    throw new PrivacyViolation(`${location}包含身份证号；请先删除或不可逆脱敏。`);
  }
  if (
    OPENAI_STYLE_KEY_RE.test(value) ||
    JWT_RE.test(value) ||
    CREDENTIAL_ASSIGNMENT_RE.test(value)
  ) {
    throw new PrivacyViolation(`${location}包含可能的凭据；请从请求内容中删除。`);
  }
}

export function scanSensitive(value: unknown, location: string): void {
  const stack: Array<{ value: unknown; location: string; depth: number }> = [
    { value, location, depth: 0 },
  ];
  let visited = 0;

  while (stack.length > 0) {
    const current = stack.pop();
    if (!current) break;
    visited += 1;
    if (visited > MAX_JSON_NODES || current.depth > MAX_JSON_DEPTH) {
      throw new PrivacyViolation(`${location}的 JSON 结构过于复杂。`);
    }

    if (typeof current.value === "string") {
      scanText(current.value, current.location);
      continue;
    }
    if (Array.isArray(current.value)) {
      current.value.forEach((child, index) => {
        stack.push({
          value: child,
          location: `${current.location}[${index}]`,
          depth: current.depth + 1,
        });
      });
      continue;
    }
    if (current.value !== null && typeof current.value === "object") {
      Object.entries(current.value as Record<string, unknown>).forEach(([key, child], index) => {
        scanText(key, `${current.location} 字段名`);
        if (isSensitiveField(key)) {
          throw new PrivacyViolation(`${current.location}包含凭据字段；请从请求内容中删除。`);
        }
        stack.push({
          value: child,
          location: `${current.location} 字段 ${index + 1}`,
          depth: current.depth + 1,
        });
      });
    }
  }
}

export function validateAnalyzePayload(
  project: unknown,
  evidence: unknown,
  auditReport: unknown | null,
): void {
  ensureJsonSize(project, "project", MAX_PROJECT_BYTES);
  ensureJsonSize(evidence, "evidence", MAX_EVIDENCE_BYTES);
  scanSensitive(project, "project");
  scanSensitive(evidence, "evidence");
  if (auditReport !== null) {
    ensureJsonSize(auditReport, "audit_report", MAX_AUDIT_REPORT_BYTES);
    scanSensitive(auditReport, "audit_report");
  }
}

export function validateApiKey(value: string | null): string {
  if (value === null || value.trim().length === 0) {
    throw new PrivacyViolation("缺少 X-Vibio-Api-Key 请求头。");
  }
  if (value !== value.trim() || value.length > MAX_API_KEY_LENGTH || /[\u0000-\u0020\u007f]/.test(value)) {
    throw new PrivacyViolation("X-Vibio-Api-Key 格式无效。");
  }
  return value;
}

export async function readBoundedJson(request: Request): Promise<unknown> {
  const contentLength = request.headers.get("content-length");
  if (contentLength !== null) {
    if (!/^\d+$/.test(contentLength)) {
      throw new PublicHttpError(400, "Content-Length 无效。");
    }
    const declaredBytes = Number(contentLength);
    if (!Number.isSafeInteger(declaredBytes)) {
      throw new PublicHttpError(400, "Content-Length 无效。");
    }
    if (declaredBytes > MAX_REQUEST_BYTES) {
      throw new PublicHttpError(413, "请求体过大。");
    }
  }

  const bytes = await request.arrayBuffer();
  if (bytes.byteLength > MAX_REQUEST_BYTES) {
    throw new PublicHttpError(413, "请求体过大。");
  }

  let text: string;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return JSON.parse(text) as unknown;
  } catch {
    throw new PublicHttpError(400, "请求体必须是有效 UTF-8 JSON。");
  }
}
