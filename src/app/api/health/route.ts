export const runtime = "nodejs";

export function GET(): Response {
  return Response.json(
    {
      status: "ok",
      service: "vibio-seo-web-api",
      version: "0.1.0",
    },
    { headers: { "Cache-Control": "public, max-age=60" } },
  );
}
