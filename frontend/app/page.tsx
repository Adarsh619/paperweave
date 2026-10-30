import Link from "next/link";

import AskBox from "@/components/AskBox";
import { askHref, EXAMPLE_QUESTIONS } from "@/lib/examples";

const STATS = [
  ["500", "influential AI/LLM papers"],
  ["4,172", "citation links"],
  ["2,653", "methods, datasets & tasks"],
];

const STEPS = [
  ["Plan", "The agent reads your question and decides what kind it is: lineage, comparison, dataset, recent work…"],
  ["Retrieve", "It queries a Neo4j knowledge graph, hybrid vector search and live arXiv, and retries if the evidence is thin."],
  ["Answer", "It writes a cited answer, checks every arXiv ID against the evidence, and shows you the graph behind it."],
];

export default function Home() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-14">
      <section className="text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">See how AI research connects</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted">
          Ask about RAG, LLM agents, retrieval, long context or hallucination. PaperWeave answers with citations and
          shows the knowledge graph of papers and methods behind every answer.
        </p>
        <div className="mx-auto mt-8 max-w-2xl">
          <AskBox autoFocus />
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted">Try an example (instant)</h2>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {EXAMPLE_QUESTIONS.map((q) => (
            <li key={q}>
              <Link
                href={askHref(q)}
                className="block h-full rounded-lg border border-border bg-surface px-4 py-3 text-sm hover:border-accent"
              >
                {q}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-14 grid gap-4 sm:grid-cols-3">
        {STATS.map(([n, label]) => (
          <div key={label} className="rounded-lg border border-border bg-surface p-5 text-center">
            <div className="text-2xl font-semibold">{n}</div>
            <div className="mt-1 text-sm text-muted">{label}</div>
          </div>
        ))}
      </section>

      <section className="mt-14">
        <h2 className="text-xl font-semibold">How it works</h2>
        <ol className="mt-4 grid gap-4 sm:grid-cols-3">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="rounded-lg border border-border bg-surface p-5">
              <div className="text-sm font-medium text-accent">
                {i + 1}. {title}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-sm text-muted">
          Plain vector search can find a paper that matches your words. It can&apos;t follow &ldquo;method A improves on
          method B, which was evaluated on dataset C&rdquo;. The graph can.
        </p>
      </section>
    </div>
  );
}
