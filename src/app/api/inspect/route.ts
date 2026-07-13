import { inspectSite, SeoInspectError, validateAuditUrl } from "../../../lib/server/seo-inspect";
import { PrivacyViolation, validateApiKey } from "../../../lib/server/privacy";
import { consumeInspectBudget } from "../../../lib/server/rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const MAX_REQUEST_BYTES = 16 * 1024;
const ALLOWED_FIELDS = new Set(["url", "max_pages", "production"]);

function jsonResponse(body: unknown, status: number, headers?: Record<string, string>): Response {
  return Response.json(body, {
    status,
    headers: {
      "cache-control": "no-store",
      ...headers,
    },
  });
}

export async function POST(request: Request): Promise<Response> {
  const contentLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(contentLength) && contentLength > MAX_REQUEST_BYTES) {
    return jsonResponse({ detail: "请求体过大。" }, 413);
  }

  let body: unknown;
  try {
    const text = await request.text();
    if (new TextEncoder().encode(text).byteLength > MAX_REQUEST_BYTES) {
      return jsonResponse({ detail: "请求体过大。" }, 413);
    }
    body = JSON.parse(text);
  } catch {
    return jsonResponse({ detail: "请求体必须是有效 JSON。" }, 400);
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return jsonResponse({ detail: "请求字段无效。" }, 422);
  }
  const record = body as Record<string, unknown>;
  if (Object.keys(record).some((key) => !ALLOWED_FIELDS.has(key))) {
    return jsonResponse({ detail: "请求包含不支持的字段。" }, 422);
  }
  if (typeof record.url !== "string") return jsonResponse({ detail: "url 必须是字符串。" }, 422);
  const maxPages = record.max_pages ?? 5;
  const production = record.production ?? false;
  if (!Number.isInteger(maxPages) || (maxPages as number) < 1 || (maxPages as number) > 10) {
    return jsonResponse({ detail: "max_pages 必须是 1 到 10 的整数。" }, 422);
  }
  if (typeof production !== "boolean") return jsonResponse({ detail: "production 必须是布尔值。" }, 422);

  let apiKey: string;
  try {
    apiKey = validateApiKey(request.headers.get("X-Vibio-Api-Key"));
  } catch (error) {
    const detail = error instanceof PrivacyViolation ? error.message : "API 密钥格式无效。";
    return jsonResponse({ detail }, 401);
  }
  const budget = consumeInspectBudget(request, apiKey);
  if (!budget.allowed) {
    return jsonResponse(
      { detail: "URL 审计请求过于频繁，请稍后重试。" },
      429,
      { "retry-after": String(budget.retryAfterSeconds) },
    );
  }

  try {
    validateAuditUrl(record.url);
    const result = await inspectSite({ url: record.url, max_pages: maxPages as number, production });
    return jsonResponse(result, 200);
  } catch (error) {
    if (error instanceof SeoInspectError) return jsonResponse({ detail: error.message }, error.status);
    return jsonResponse({ detail: "无法完成站点源码审计。" }, 500);
  }
}
