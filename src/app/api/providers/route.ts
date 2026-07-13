import { publicProviderCatalog } from "../../../lib/server/providers";

export const runtime = "nodejs";

export function GET(): Response {
  return Response.json(
    { providers: publicProviderCatalog() },
    { headers: { "Cache-Control": "public, max-age=300, stale-while-revalidate=3600" } },
  );
}
