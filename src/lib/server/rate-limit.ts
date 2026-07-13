import { createHash } from "node:crypto";

interface Bucket {
  count: number;
  resetAt: number;
}

interface RateLimitResult {
  allowed: boolean;
  retryAfterSeconds: number;
}

const WINDOW_MS = 60_000;
const KEY_LIMIT = 6;
const IP_LIMIT = 20;
const buckets = new Map<string, Bucket>();

function digest(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}

function clientAddress(request: Request): string {
  const realIp = request.headers.get("x-real-ip")?.trim();
  if (realIp) return realIp;
  return request.headers.get("x-forwarded-for")?.split(",", 1)[0]?.trim() || "unknown";
}

function consume(key: string, limit: number, now: number): RateLimitResult {
  const current = buckets.get(key);
  if (!current || current.resetAt <= now) {
    buckets.set(key, { count: 1, resetAt: now + WINDOW_MS });
    return { allowed: true, retryAfterSeconds: 0 };
  }
  if (current.count >= limit) {
    return {
      allowed: false,
      retryAfterSeconds: Math.max(1, Math.ceil((current.resetAt - now) / 1_000)),
    };
  }
  current.count += 1;
  return { allowed: true, retryAfterSeconds: 0 };
}

export function consumeInspectBudget(
  request: Request,
  apiKey: string,
  now = Date.now(),
): RateLimitResult {
  if (buckets.size > 2_000) {
    for (const [key, bucket] of buckets) {
      if (bucket.resetAt <= now) buckets.delete(key);
    }
  }

  const keyResult = consume(`key:${digest(apiKey)}`, KEY_LIMIT, now);
  if (!keyResult.allowed) return keyResult;

  const address = clientAddress(request);
  if (address === "unknown") return keyResult;
  return consume(`ip:${digest(address)}`, IP_LIMIT, now);
}
