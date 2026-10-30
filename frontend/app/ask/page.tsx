import type { Metadata } from "next";
import { Suspense } from "react";

import AskView from "@/components/AskView";

export const metadata: Metadata = { title: "Ask · PaperWeave" };

// AskView reads ?q= from the URL, so it renders on the client inside a Suspense boundary.
export default function AskPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-8 text-sm text-muted">Loading…</div>}>
      <AskView />
    </Suspense>
  );
}
