import type { Metadata } from "next";
import Link from "next/link";

import type { CoverageStats } from "@/lib/types";
import coverage from "@/public/stats.json";

export const metadata: Metadata = { title: "How it works · PaperWeave" };

const stats = coverage as CoverageStats;

const PIPELINE = [
  ["Collect", "The most cited arXiv papers per topic and per year come from the Semantic Scholar API, plus the citation links between them."],
  ["Extract", "A small open-source LLM (Qwen3 4B, run locally with Ollama) reads every abstract and pulls out the methods, datasets and tasks it names."],
  ["Clean", "Spellings of the same thing are merged (“RAG” = “Retrieval-Augmented Generation”); vague names and citations are dropped."],
  ["Store", "A Neo4j knowledge graph holds papers, authors, methods and their links. A Qdrant index holds each paper for meaning + keyword search."],
];

const AGENT = [
  ["Plan", "An LLM decides what kind of question it is (lineage, comparison, dataset, top-cited, recent…) and which names it mentions."],
  ["Retrieve", "Code, not the LLM, picks the tools: graph queries, hybrid search, a search per named method, and live arXiv for recent work."],
  ["Check", "If the evidence is thin, it rewrites the query and tries again (up to twice)."],
  ["Answer", "A stronger LLM writes the answer. Every [arXiv ID] is checked against the retrieved papers: garbled ones are fixed, invented ones removed."],
  ["Show", "The papers, methods and datasets behind the answer become the graph you can explore."],
];

// From README "Evaluation" (backend/evals/results.md): 40 scored golden questions, local Qwen3 4B.
const EVAL = [
  ["All", "40", "71%", "82%", "69%", "78%"],
  ["Lookup", "17", "100%", "100%", "100%", "94%"],
  ["Multi-hop", "11", "32%", "42%", "29%", "39%"],
  ["Comparison", "12", "65%", "92%", "61%", "92%"],
  ["Physics & math", "10", "95%", "95%", "95%", "95%"],
];

const STACK = [
  ["Frontend", "Next.js, React, Tailwind CSS, react-force-graph (Vercel)"],
  ["Backend", "FastAPI, LangGraph, Docker (Render)"],
  ["Graph database", "Neo4j (AuraDB Free)"],
  ["Vector search", "Qdrant: MiniLM embeddings + BM25, fused with RRF"],
  ["LLMs", "Groq (Llama 3.3 70B), Gemini fallback; Ollama for the offline graph build"],
  ["Data", "Semantic Scholar API, arXiv API"],
];

function Steps({ items }: { items: string[][] }) {
  return (
    <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map(([title, text], i) => (
        <li key={title} className="rounded-lg border border-border bg-surface p-4">
          <div className="text-sm font-medium text-accent">
            {i + 1}. {title}
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-muted">{text}</p>
        </li>
      ))}
    </ol>
  );
}

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-serif text-4xl font-semibold tracking-tight">How PaperWeave works</h1>
      <p className="mt-3 max-w-3xl text-muted">
        PaperWeave answers research questions from {stats.totals.papers.toLocaleString()} influential arXiv papers. It
        combines a knowledge graph (which paper proposed which method, what improved on what, who evaluated on which
        dataset) with semantic search, so it can answer questions that need links between papers, not just matching
        text.
      </p>

      <section className="mt-12">
        <h2 className="font-serif text-2xl font-semibold">1. Building the library (offline)</h2>
        <Steps items={PIPELINE} />
      </section>

      <section className="mt-12">
        <h2 className="font-serif text-2xl font-semibold">2. Answering a question (live)</h2>
        <Steps items={AGENT} />
        <p className="mt-4 text-sm text-muted">
          Safety: graph queries written by the LLM must pass a read-only check and also run in a read-only database
          transaction, so they can never change the data.
        </p>
      </section>

      <section className="mt-12">
        <h2 className="font-serif text-2xl font-semibold">3. Does the graph help? The evaluation</h2>
        <p className="mt-2 max-w-3xl text-sm text-muted">
          40 test questions across AI, physics and math, each with the papers a correct answer must use (the physics &amp;
          math row overlaps the others).
          3 more off-topic questions check that PaperWeave politely declines: it declined all 3. Both systems may show the answer model at
          most 12 papers. &ldquo;Vector-only&rdquo; is the same search without the graph or the agent.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] border-collapse text-sm">
            <thead>
              <tr className="bg-accent-soft text-left">
                {["Questions", "n", "Papers found: vector-only", "PaperWeave", "Papers cited: vector-only", "PaperWeave"].map(
                  (h, i) => (
                    <th key={i} className="border border-border px-3 py-2 font-semibold">
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {EVAL.map((row) => (
                <tr key={row[0]}>
                  {row.map((cell, i) => (
                    <td key={i} className={`border border-border px-3 py-2 ${i === 3 || i === 5 ? "font-semibold" : ""}`}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ul className="mt-4 list-disc space-y-1.5 pl-5 text-sm text-muted">
          <li>The graph helps most where plain search can&apos;t follow links: comparisons went from 65% to 92%, and &ldquo;which papers build on Attention Is All You Need?&rdquo; from 0% to 60%.</li>
          <li>Simple lookups are easy in every field: both systems find the right paper for all 17, physics and math included.</li>
          <li>
            Honest limitation: multi-hop questions are the weak spot. The small planning model often treats them as simple
            lookups, so they never reach the graph. A larger model should help.
          </li>
        </ul>
      </section>

      <section className="mt-12 grid gap-8 sm:grid-cols-2">
        <div>
          <h2 className="font-serif text-2xl font-semibold">Tech stack</h2>
          <dl className="mt-4 space-y-2 text-sm">
            {STACK.map(([k, v]) => (
              <div key={k}>
                <dt className="font-medium">{k}</dt>
                <dd className="text-muted">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div>
          <h2 className="font-serif text-2xl font-semibold">Free to run</h2>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            Everything runs on free tiers. The backend sleeps when idle, so a first question can take up to a minute;
            the example questions are saved answers and load instantly. New questions are limited to 15 per hour per
            visitor.
          </p>
          <p className="mt-4 text-sm">
            <a href="https://github.com/Adarsh619/paperweave" className="text-accent underline" target="_blank" rel="noreferrer">
              Source code on GitHub
            </a>{" "}
            ·{" "}
            <Link href="/" className="text-accent underline">
              Try it
            </Link>
          </p>
        </div>
      </section>
    </div>
  );
}
