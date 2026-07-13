import type { Metadata } from "next";

import { Workspace } from "@/components/Workspace";

export const metadata: Metadata = {
  title: "Vibio SEO 工作台",
  robots: {
    index: false,
    follow: false,
  },
};

export default function WorkspacePage() {
  return (
    <div className="min-h-screen bg-[#f3f4f0] text-[#181c23]">
      <Workspace />
    </div>
  );
}
