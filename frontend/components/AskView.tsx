"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import AgentSteps from "@/components/AgentSteps";
import Answer from "@/components/Answer";
import AskBox from "@/components/AskBox";
import Citations from "@/components/Citations";
import GraphView from "@/components/GraphView";
import PaperPanel from "@/components/PaperPanel";
import WakingBanner from "@/components/WakingBanner";
import { streamChat } from "@/lib/api";
import { findExample } from "@/lib/examples";
import type { ChatEvent, Citation, Step, Subgraph } from "@/lib/types";

type Status = "loading" | "streaming" | "done" | "error";
type Source = "example" | "cached" | "live";

const EMPTY_GRAPH: Subgraph = { nodes: [], links: [] };
// No response at all after this long means the free-tier server is booting.
const WAKING_AFTER_MS = 4000;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function AskView() {
  const question = useSearchParams().get("q")?.trim() ?? "";
  if (question.length < 3) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <AskBox autoFocus />
      </div>
    );
  }
  // Keyed by question: asking something new remounts with fresh state.
  return <QuestionRun key={question} question={question} />;
}

function QuestionRun({ question }: { question: string }) {
  const [status, setStatus] = useState<Status>("loading");
  const [source, setSource] = useState<Source>("live");
  const [steps, setSteps] = useState<Step[]>([]);
  const [text, setText] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [graph, setGraph] = useState<Subgraph>(EMPTY_GRAPH);
  const [error, setError] = useState("");
  const [waking, setWaking] = useState(false);
  const [open, setOpen] = useState<Citation | null>(null);

  const handle = useCallback((e: ChatEvent) => {
    switch (e.event) {
      case "step":
        setSteps((s) => [...s, e.data]);
        break;
      case "token":
        setText((t) => t + e.data.text);
        break;
      case "answer":
        setText(e.data.text); // the verified answer replaces the raw token stream
        break;
      case "citations":
        setCitations(e.data);
        break;
      case "subgraph":
        setGraph(e.data);
        break;
      case "error":
        setError(e.data.message);
        setStatus("error");
        break;
      case "done":
        setSource(e.data.cached ? "cached" : "live");
        setStatus((s) => (s === "error" ? s : "done"));
        break;
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      const example = await findExample(question);
      if (controller.signal.aborted) return;
      if (example) {
        // Saved answer: replay the steps with a short delay so the timeline still reads naturally.
        setSource("example");
        setStatus("streaming");
        for (const e of example.events) {
          if (controller.signal.aborted) return;
          if (e.event === "step") await sleep(250);
          handle(e);
        }
        setStatus("done");
        return;
      }
      setStatus("streaming");
      const timer = setTimeout(() => setWaking(true), WAKING_AFTER_MS);
      try {
        await streamChat(question, handle, controller.signal, () => {
          clearTimeout(timer);
          setWaking(false);
        });
      } catch (err) {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : String(err);
        setError(
          message === "Failed to fetch"
            ? "Couldn't reach the PaperWeave server. Try again in a minute, or pick an example question."
            : message,
        );
        setStatus("error");
      } finally {
        clearTimeout(timer);
        setWaking(false);
      }
    })();

    return () => controller.abort();
  }, [question, handle]);

  const openId = (id: string) =>
    setOpen(citations.find((c) => c.arxiv_id === id) ?? { arxiv_id: id, title: id, year: null, abs_url: null, source: "graph" });

  const running = status === "loading" || status === "streaming";

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="max-w-3xl">
        <AskBox key={question} initial={question} />
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
        <div className="min-w-0 space-y-6">
          <h1 className="text-2xl font-semibold leading-snug">{question}</h1>
          {waking && <WakingBanner />}
          <AgentSteps steps={steps} running={running} />

          {error && (
            <div role="alert" className="rounded-lg border border-border px-4 py-3 text-sm">
              {error}{" "}
              <Link href="/" className="text-accent underline">
                See example questions
              </Link>
            </div>
          )}

          {text && (
            <article className="rounded-lg border border-border bg-surface p-5">
              <Answer text={text} onCite={openId} />
              {status === "done" && (
                <p className="mt-4 text-xs text-muted">
                  {source === "example"
                    ? "Saved example answer."
                    : source === "cached"
                      ? "Answered from cache."
                      : "Answered live."}{" "}
                  Every citation was checked against the retrieved papers.
                </p>
              )}
            </article>
          )}

          <Citations items={citations} onOpen={setOpen} />
        </div>

        <aside className="min-w-0 lg:sticky lg:top-6 lg:self-start">
          <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-muted">Graph behind the answer</h2>
          {graph.nodes.length > 0 ? (
            <GraphView graph={graph} onPaper={openId} />
          ) : (
            <div className="flex h-[420px] items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted">
              {running ? "The graph appears when the answer is ready." : "No graph for this answer."}
            </div>
          )}
        </aside>
      </div>

      <PaperPanel citation={open} onClose={() => setOpen(null)} />
    </div>
  );
}
