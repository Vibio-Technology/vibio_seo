import type { Metadata } from "next";

import { Workspace } from "@/components/Workspace";

export const metadata: Metadata = {
  title: "Vibio SEO 工作台",
  alternates: {
    canonical: "/workspace",
  },
  robots: {
    index: false,
    follow: false,
  },
};

export default function WorkspacePage() {
  return (
    <div className="min-h-screen bg-[#f7f9fc] text-[#172033]">
      <Workspace />
    </div>
  );
}
