"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AgentSteps from "@/components/AgentSteps";
import Answer from "@/components/Answer";
import Citations from "@/components/Citations";
import GraphView from "@/components/GraphView";
import PaperPanel from "@/components/PaperPanel";
import { askHref, finishedAnswer, findExample } from "@/lib/examples";
import type { Citation } from "@/lib/types";

const SHOWCASE = "Compare GraphRAG, RAPTOR and HippoRAG";

/** A real saved answer, shown on the home page so visitors see the output before asking.
 *  Read from examples.json: no backend call, so it works while the server sleeps. */
export default function HomeExample() {
  const [answer, setAnswer] = useState<ReturnType<typeof finishedAnswer> | null>(null);
  const [open, setOpen] = useState<Citation | null>(null);

  useEffect(() => {
    findExample(SHOWCASE).then((e) => e && setAnswer(finishedAnswer(e)));
  }, []);

  if (!answer) return null;
  const openId = (id: string) => setOpen(answer.citations.find((c) => c.arxiv_id === id) ?? null);

  return (
    <div className="rounded-xl border border-border bg-surface p-4 sm:p-6">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">Example question</div>
      <div className="mt-1 text-lg font-semibold">{SHOWCASE}</div>
      <div className="mt-5 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
        <div className="min-w-0 space-y-5">
          <details className="text-sm">
            <summary className="cursor-pointer text-muted">What the agent did ({answer.steps.length} steps)</summary>
            <div className="mt-3">
              <AgentSteps steps={answer.steps} running={false} />
            </div>
          </details>
          <Answer text={answer.text} onCite={openId} />
          <Citations items={answer.citations} onOpen={setOpen} />
        </div>
        <div className="min-w-0">
          <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">Graph behind the answer</div>
          <GraphView graph={answer.graph} height={320} />
        </div>
      </div>
      <Link href={askHref(SHOWCASE)} className="mt-5 inline-block text-sm text-accent underline">
        Open it full-size, or ask your own →
      </Link>
      <PaperPanel citation={open} onClose={() => setOpen(null)} />
    </div>
  );
}
