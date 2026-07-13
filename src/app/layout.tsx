import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import "./globals.css";

function siteUrl(): URL {
  const configured = process.env.NEXT_PUBLIC_SITE_URL;
  const vercelHost = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  const candidate = configured || (vercelHost ? `https://${vercelHost}` : "http://localhost:3000");

  try {
    return new URL(/^https?:\/\//i.test(candidate) ? candidate : `https://${candidate}`);
  } catch {
    return new URL("http://localhost:3000");
  }
}

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  title: {
    default: "Vibio SEO | 证据驱动的搜索优化工作流",
    template: "%s | Vibio SEO",
  },
  description:
    "Vibio SEO 把审计、关键词、计划、修复草案、内容、链接与复盘连成一条有证据、可执行、可验证的 SEO 工作流。",
  applicationName: "Vibio SEO",
  authors: [{ name: "Vibio" }],
  creator: "Vibio",
  publisher: "Vibio",
  category: "technology",
  alternates: {
    canonical: "/",
  },
  icons: {
    icon: "/vibio-logo.png",
    apple: "/vibio-logo.png",
  },
  manifest: "/manifest.webmanifest",
  openGraph: {
    type: "website",
    locale: "zh_CN",
    url: "/",
    siteName: "Vibio SEO",
    title: "Vibio SEO | 证据驱动的搜索优化工作流",
    description: "把 SEO 从一堆建议，变成有证据、能执行、可复盘的工作流。",
    images: [
      {
        url: "/vibio-workspace-preview.webp",
        width: 1440,
        height: 1000,
        alt: "Vibio SEO 工作台",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Vibio SEO | 证据驱动的搜索优化工作流",
    description: "有证据、能执行、可复盘的 SEO 工作流。",
    images: ["/vibio-workspace-preview.webp"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f3f4f0",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
