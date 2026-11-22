import Link from "next/link";

import AskBox from "@/components/AskBox";
import HomeExample from "@/components/HomeExample";
import { Card, HeroThreads, Reveal } from "@/components/Motion";
import BlurText from "@/components/reactbits/BlurText";
import CountUp from "@/components/reactbits/CountUp";
import { askHref, EXAMPLE_QUESTIONS } from "@/lib/examples";
import type { CoverageStats } from "@/lib/types";
import coverage from "@/public/stats.json";

const stats = coverage as CoverageStats;
const HEADLINE = "See how research connects";

const PITCH = [
  [
    "What it is",
    "A research assistant for AI, computer science and physics papers. Ask a question; it reads the papers and the links between them, then answers with sources.",
  ],
  [
    "Who it's for",
    "Students getting into a field, engineers choosing a method, and researchers who want to see what built on what.",
  ],
  [
    "Why not just ChatGPT?",
    "Every claim cites a real paper, and every citation is checked against the papers it actually retrieved. It also follows links like “method A improves on B” and shows you that graph.",
  ],
];

const GOOD = [
  "What improved on RAG?",
  "Compare Self-RAG and Corrective RAG",
  "Which papers evaluate on HotpotQA?",
  "What are the latest papers on agent memory?",
];
const NOT_COVERED = [
  "General chat, coding help or writing (“write me an email”)",
  "News, products and prices (“is GPT-5 better than Claude?”)",
  "Fields outside its library, like medicine or economics",
  "Opinions or forecasts: it reports what the papers show",
];

const STEPS = [
  ["Plan", "The agent reads your question and decides what kind it is: lineage, comparison, dataset, recent work…"],
  ["Retrieve", "It queries a Neo4j knowledge graph, hybrid vector search and live arXiv, and retries if the evidence is thin."],
  ["Answer", "It writes a cited answer, checks every arXiv ID against the evidence, and shows you the graph behind it."],
];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="font-serif text-2xl font-semibold tracking-tight">{children}</h2>;
}

export default function Home() {
  const { totals } = stats;
  return (
    <div>
      <section className="relative overflow-hidden border-b border-border">
        <div className="pointer-events-none absolute inset-0">
          <HeroThreads />
        </div>
        <div className="relative mx-auto max-w-3xl px-4 pt-20 pb-16 text-center sm:pt-28 sm:pb-24">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-accent">A research assistant you can check</p>
          <h1 className="sr-only">{HEADLINE}</h1>
          <div aria-hidden>
            <BlurText
              text={HEADLINE}
              animateBy="words"
              delay={90}
              className="mt-4 justify-center font-serif text-4xl font-semibold tracking-tight sm:text-6xl"
            />
          </div>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-muted">
            Ask about AI, computer science or physics research. PaperWeave answers with citations and shows the
            knowledge graph of papers and methods behind every answer.
          </p>
          <div className="mx-auto mt-8 max-w-2xl">
            <AskBox autoFocus />
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-5xl px-4 py-16">
        <Reveal>
          <section>
            <SectionTitle>See it in action</SectionTitle>
            <p className="mt-1 mb-4 text-sm text-muted">A real answer, exactly as PaperWeave produced it.</p>
            <HomeExample />
          </section>
        </Reveal>

        <Reveal className="mt-16">
          <section className="grid gap-4 sm:grid-cols-3">
            {PITCH.map(([title, text]) => (
              <Card key={title}>
                <h2 className="font-serif text-lg font-semibold">{title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
              </Card>
            ))}
          </section>
        </Reveal>

        <Reveal className="mt-16">
          <section>
            <SectionTitle>Try an example (instant)</SectionTitle>
            <ul className="mt-4 grid gap-2 sm:grid-cols-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <li key={q}>
                  <Link
                    href={askHref(q)}
                    className="group flex h-full items-center justify-between gap-3 rounded-lg border border-border bg-surface px-4 py-3 text-sm transition-colors hover:border-accent"
                  >
                    {q}
                    <span aria-hidden className="text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent">
                      →
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </Reveal>

        <Reveal className="mt-16">
          <section>
            <SectionTitle>What it knows</SectionTitle>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              {[
                [totals.papers, "influential arXiv papers"],
                [totals.citations, "citation links between them"],
                [totals.entities, "methods, datasets & tasks"],
              ].map(([n, label]) => (
                <div key={label} className="rounded-xl border border-border bg-surface p-5 text-center">
                  <CountUp to={n as number} separator="," duration={1.4} className="font-serif text-3xl font-semibold" />
                  <div className="mt-1 text-sm text-muted">{label}</div>
                </div>
              ))}
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {stats.fields.map((f) => (
                <div key={f.name} className="rounded-xl border border-border bg-surface p-5">
                  <div className="flex items-baseline justify-between gap-2">
                    <h3 className="font-serif text-lg font-semibold">{f.name}</h3>
                    <span className="text-xs text-muted">{f.papers.toLocaleString()} papers</span>
                  </div>
                  <ul className="mt-3 flex flex-wrap gap-1.5">
                    {f.topics.map((t) => (
                      <li key={t.name} className="rounded-full border border-border px-2.5 py-0.5 text-xs">
                        {t.name} <span className="text-muted">{t.papers}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        </Reveal>

        <Reveal className="mt-16">
          <section className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface p-5">
              <h2 className="font-serif text-lg font-semibold">Good questions</h2>
              <ul className="mt-3 space-y-1.5 text-sm">
                {GOOD.map((q) => (
                  <li key={q}>
                    <Link href={askHref(q)} className="text-accent hover:underline">
                      {q}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <h2 className="font-serif text-lg font-semibold">Not what it&apos;s for</h2>
              <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-muted">
                {NOT_COVERED.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          </section>
        </Reveal>

        <Reveal className="mt-16">
          <section>
            <SectionTitle>How it works</SectionTitle>
            <ol className="mt-4 grid gap-4 sm:grid-cols-3">
              {STEPS.map(([title, text], i) => (
                <li key={title} className="rounded-xl border border-border bg-surface p-5">
                  <div className="font-serif text-3xl text-accent">{i + 1}</div>
                  <div className="mt-1 font-medium">{title}</div>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{text}</p>
                </li>
              ))}
            </ol>
            <p className="mt-4 text-sm text-muted">
              Plain vector search finds papers that match your words. It can&apos;t follow &ldquo;method A improves on
              method B, which was evaluated on dataset C&rdquo;. The graph can.{" "}
              <Link href="/how-it-works" className="text-accent underline">
                Read how it works →
              </Link>
            </p>
          </section>
        </Reveal>
      </div>
    </div>
  );
}
