import { Suspense } from "react";

import PaperView from "@/components/PaperView";

// Paper IDs aren't known at build time, so PaperView reads the param on the client.
export default function PaperPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-4xl px-4 py-10 text-sm text-muted">Loading…</div>}>
      <PaperView />
    </Suspense>
  );
}
