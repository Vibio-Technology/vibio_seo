import type { MetadataRoute } from "next";

function publicSiteUrl(): URL {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  const vercelHost = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  const candidate = configured || (vercelHost ? `https://${vercelHost}` : "http://localhost:3000");

  try {
    return new URL(/^https?:\/\//i.test(candidate) ? candidate : `https://${candidate}`);
  } catch {
    return new URL("http://localhost:3000");
  }
}

export default function sitemap(): MetadataRoute.Sitemap {
  const base = publicSiteUrl();
  const lastModified = new Date("2026-07-13T00:00:00+08:00");

  return [
    {
      url: new URL("/", base).toString(),
      lastModified,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: new URL("/workspace", base).toString(),
      lastModified,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: new URL("/privacy", base).toString(),
      lastModified,
      changeFrequency: "monthly",
      priority: 0.4,
    },
  ];
}
