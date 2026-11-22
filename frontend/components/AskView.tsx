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
import { useSmoothText } from "@/lib/useSmoothText";
import type { ChatEvent, Citation, Step, Subgraph, Turn } from "@/lib/types";

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
  // Keyed by question: asking something new remounts with a fresh conversation.
  return <Conversation key={question} first={question} />;
}

/** The first question plus any follow-ups, each answered with the earlier turns as context. */
function Conversation({ first }: { first: string }) {
  const [questions, setQuestions] = useState([first]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const onDone = useCallback((index: number, answer: string) => {
    setAnswers((a) => Object.assign([...a], { [index]: answer }));
  }, []);
  const last = questions.length - 1;
  const canFollowUp = answers[last] !== undefined && draft.trim().length >= 3;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="max-w-3xl">
        <AskBox initial={first} />
      </div>
      {questions.map((q, i) => (
        <QuestionRun
          key={i}
          index={i}
          question={q}
          history={questions.slice(0, i).map((question, j) => ({ question, answer: answers[j] ?? "" }))}
          onDone={onDone}
        />
      ))}
      {answers[last] !== undefined && (
        <form
          className="mt-10 flex max-w-3xl gap-2 border-t border-border pt-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (!canFollowUp) return;
            setQuestions((qs) => [...qs, draft.trim()]);
            setDraft("");
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            maxLength={500}
            placeholder="Ask a follow-up, e.g. “Which of these is the newest?”"
            aria-label="Follow-up question"
            className="min-w-0 flex-1 rounded-lg border border-border bg-surface px-4 py-3 outline-none focus:border-accent"
          />
          <button
            type="submit"
            disabled={!canFollowUp}
            className="rounded-lg bg-accent px-5 py-3 font-medium text-on-accent transition-opacity hover:opacity-90 disabled:opacity-40"
          >
            Follow up
          </button>
        </form>
      )}
    </div>
  );
}

function QuestionRun({
  index,
  question,
  history,
  onDone,
}: {
  index: number;
  question: string;
  history: Turn[];
  onDone: (index: number, answer: string) => void;
}) {
  // The conversation so far, frozen when this turn starts (later turns don't change it).
  const [context] = useState(history);
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
    let finalAnswer: string | null = null;
    const onEvent = (e: ChatEvent) => {
      if (e.event === "answer") finalAnswer = e.data.text;
      handle(e);
    };
    (async () => {
      // Saved examples only make sense without earlier turns.
      const example = context.length ? null : await findExample(question);
      if (controller.signal.aborted) return;
      if (example) {
        // Saved answer: replay the steps with a short delay so the timeline still reads naturally.
        setSource("example");
        setStatus("streaming");
        for (const e of example.events) {
          if (controller.signal.aborted) return;
          if (e.event === "step") await sleep(250);
          onEvent(e);
        }
        setStatus("done");
        if (finalAnswer !== null) onDone(index, finalAnswer);
        return;
      }
      setStatus("streaming");
      const timer = setTimeout(() => setWaking(true), WAKING_AFTER_MS);
      try {
        await streamChat(
          question,
          onEvent,
          controller.signal,
          () => {
            clearTimeout(timer);
            setWaking(false);
          },
          context,
        );
        if (finalAnswer !== null) onDone(index, finalAnswer);
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
  }, [question, handle, context, index, onDone]);

  const openId = (id: string) =>
    setOpen(citations.find((c) => c.arxiv_id === id) ?? { arxiv_id: id, title: id, year: null, abs_url: null, source: "graph" });

  const shown = useSmoothText(text);
  const running = status === "loading" || status === "streaming";

  const Heading = index === 0 ? "h1" : "h2";

  return (
    <section className={index === 0 ? "" : "mt-12 border-t border-border pt-8"}>
      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
        <div className="min-w-0 space-y-6">
          {index > 0 && <div className="text-xs font-medium uppercase tracking-wide text-accent">Follow-up</div>}
          <Heading className="font-serif text-2xl font-semibold leading-snug">{question}</Heading>
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
              <Answer text={shown} onCite={openId} />
              {status === "done" && shown === text && (
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
    </section>
  );
}
