import type { Metadata } from "next";
import Link from "next/link";

import type { CoverageStats } from "@/lib/types";
import coverage from "@/public/stats.json";

export const metadata: Metadata = { title: "About · PaperWeave" };

const stats = coverage as CoverageStats;
const REPO = "https://github.com/Adarsh619/paperweave";

const PRINCIPLES = [
  ["Checkable", "Every claim cites an arXiv paper, and every citation is checked against the papers the agent actually retrieved. Invented IDs are removed before you see the answer."],
  ["Connected", "Papers aren't isolated documents. PaperWeave follows the links between them (what improved on what, who evaluated on which dataset) and shows you that graph."],
  ["Honest", "It says when the evidence is thin, declines questions outside research papers, and reports trends as measurements from the data, never forecasts."],
];

const LIMITS = [
  "The library is a snapshot of the most cited papers per topic and year, not all of arXiv. Very new or niche work may be missing; the “latest papers” questions search arXiv live to cover that.",
  "Methods, datasets and tasks were extracted from abstracts by a small open-source model, so some names in the graph are noisy or missing.",
  "It reads abstracts and metadata, not full paper text.",
  "Questions that chain several links (“what improved on X, and which datasets did those use?”) are the hardest; the evaluation on the How it works page shows where it falls short.",
  "Answers can still be wrong. The citations are there so you can check.",
];

const CREDITS = [
  ["Semantic Scholar", "paper metadata, citation counts and citation links"],
  ["arXiv", "papers, abstracts and live search"],
  ["Neo4j, Qdrant, LangGraph", "the graph, the search index and the agent"],
  ["Groq", "fast hosted open-weight LLMs for answers"],
  ["Next.js, React Bits", "the site and its animations"],
];

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="font-serif text-2xl font-semibold tracking-tight">{children}</h2>;
}

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="font-serif text-4xl font-semibold tracking-tight">About PaperWeave</h1>
      <p className="mt-4 max-w-3xl text-lg leading-relaxed text-muted">
        Research moves fast, and the hard part is rarely finding one paper. It&apos;s seeing how the papers connect:
        which idea built on which, what replaced what, and where the evidence actually comes from. Chatbots answer
        fluently but can&apos;t show their sources; search engines list papers but not the links between them.
        PaperWeave does both, over {stats.totals.papers.toLocaleString()} influential papers in AI, computer science,
        physics and math.
      </p>

      <section className="mt-12">
        <SectionTitle>What it stands for</SectionTitle>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {PRINCIPLES.map(([title, text]) => (
            <div key={title} className="rounded-xl border border-border bg-surface p-5">
              <h3 className="font-serif text-lg font-semibold text-accent">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <SectionTitle>Know its limits</SectionTitle>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted">
          {LIMITS.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      </section>

      <section className="mt-12 grid gap-8 sm:grid-cols-2">
        <div>
          <SectionTitle>Data &amp; credits</SectionTitle>
          <dl className="mt-4 space-y-2 text-sm">
            {CREDITS.map(([k, v]) => (
              <div key={k}>
                <dt className="font-medium">{k}</dt>
                <dd className="text-muted">{v}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 text-xs text-muted">Thank you to arXiv for use of its open access interoperability.</p>
        </div>
        <div>
          <SectionTitle>Who built it</SectionTitle>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            PaperWeave is a personal project by Adarsh Pradhan: an end-to-end GraphRAG system, from building the
            knowledge graph to the agent, the evaluation and this site, designed to run entirely on free tiers. The
            code is open source.
          </p>
          <p className="mt-4 text-sm">
            <a href={REPO} className="text-accent underline" target="_blank" rel="noreferrer">
              Source code on GitHub
            </a>{" "}
            ·{" "}
            <Link href="/how-it-works" className="text-accent underline">
              How it works
            </Link>{" "}
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
