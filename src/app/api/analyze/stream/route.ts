import {
  prepareAnalyzeRequest,
  runPreparedAnalysis,
  toPublicAnalyzeError,
  type AnalysisResult,
  type PreparedAnalysis,
} from "../route";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;
export const HEARTBEAT_INTERVAL_MS = 10_000;

type AnalyzeStreamEvent =
  | {
      type: "accepted";
      provider: string;
      model: string;
      mode: string;
    }
  | { type: "heartbeat" }
  | { type: "complete"; result: AnalysisResult }
  | { type: "error"; status: number; detail: string };

const encoder = new TextEncoder();

function encodeEvent(event: AnalyzeStreamEvent): Uint8Array {
  return encoder.encode(`${JSON.stringify(event)}\n`);
}

function jsonError(status: number, detail: string): Response {
  return Response.json(
    { detail },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

function analysisStream(request: Request, analysis: PreparedAnalysis): ReadableStream<Uint8Array> {
  const upstreamController = new AbortController();
  let streamController: ReadableStreamDefaultController<Uint8Array> | null = null;
  let heartbeat: ReturnType<typeof setInterval> | undefined;
  let active = true;

  const cleanup = () => {
    if (heartbeat !== undefined) {
      clearInterval(heartbeat);
      heartbeat = undefined;
    }
    request.signal.removeEventListener("abort", handleRequestAbort);
  };

  const close = () => {
    try {
      streamController?.close();
    } catch {
      // The consumer may have already cancelled the stream.
    }
  };

  const stop = (reason?: unknown) => {
    if (!active) return;
    active = false;
    cleanup();
    if (!upstreamController.signal.aborted) upstreamController.abort(reason);
    close();
  };

  const send = (event: AnalyzeStreamEvent): boolean => {
    if (!active || !streamController) return false;
    try {
      streamController.enqueue(encodeEvent(event));
      return true;
    } catch {
      stop();
      return false;
    }
  };

  const finish = (event: AnalyzeStreamEvent) => {
    if (!active) return;
    send(event);
    if (!active) return;
    active = false;
    cleanup();
    close();
  };

  function handleRequestAbort(): void {
    stop(request.signal.reason);
  }

  return new ReadableStream<Uint8Array>({
    start(controller) {
      streamController = controller;
      if (request.signal.aborted) {
        stop(request.signal.reason);
        return;
      }
      request.signal.addEventListener("abort", handleRequestAbort, { once: true });
      if (!send({
        type: "accepted",
        provider: analysis.providerId,
        model: analysis.model,
        mode: analysis.mode,
      })) return;

      heartbeat = setInterval(() => {
        send({ type: "heartbeat" });
      }, HEARTBEAT_INTERVAL_MS);

      void runPreparedAnalysis(analysis, upstreamController.signal).then(
        (result) => finish({ type: "complete", result }),
        (error: unknown) => {
          const publicError = toPublicAnalyzeError(error);
          finish({ type: "error", ...publicError });
        },
      );
    },
    cancel(reason) {
      if (!active) return;
      active = false;
      cleanup();
      if (!upstreamController.signal.aborted) upstreamController.abort(reason);
    },
  });
}

export async function POST(request: Request): Promise<Response> {
  let analysis: PreparedAnalysis;
  try {
    analysis = await prepareAnalyzeRequest(request);
  } catch (error) {
    const publicError = toPublicAnalyzeError(error);
    return jsonError(publicError.status, publicError.detail);
  }

  return new Response(analysisStream(request, analysis), {
    status: 200,
    headers: {
      "Cache-Control": "no-store, no-transform",
      "Content-Type": "application/x-ndjson; charset=utf-8",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
