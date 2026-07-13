import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Vibio SEO",
    short_name: "Vibio SEO",
    description: "证据驱动的搜索优化工作流。",
    start_url: "/workspace",
    display: "standalone",
    background_color: "#f3f4f0",
    theme_color: "#175de5",
    lang: "zh-CN",
    icons: [
      {
        src: "/vibio-logo.png",
        sizes: "600x600",
        type: "image/png",
      },
    ],
  };
}
