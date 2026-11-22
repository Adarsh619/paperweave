"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getTrends } from "@/lib/api";
import type { Trends } from "@/lib/types";

const pct = (x: number) => `${x > 0 ? "+" : ""}${Math.round(x * 100)}%`;
const share = (x: number) => `${(x * 100).toFixed(1)}%`;

export default function TrendsView({ fields }: { fields: string[] }) {
  const [field, setField] = useState<string | null>(null);
  return (
    <div>
      <div role="tablist" aria-label="Field" className="flex flex-wrap gap-2">
        {[null, ...fields].map((f) => (
          <button
            key={f ?? "all"}
            role="tab"
            aria-selected={field === f}
            onClick={() => setField(f)}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${
              field === f ? "border-accent bg-accent text-on-accent" : "border-border bg-surface hover:border-accent"
            }`}
          >
            {f ?? "All fields"}
          </button>
        ))}
      </div>
      {/* Keyed by field so switching starts a fresh load. */}
      <TrendsData key={field ?? "all"} field={field} />
    </div>
  );
}

function TrendsData({ field }: { field: string | null }) {
  const [data, setData] = useState<Trends | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getTrends(field ?? undefined)
      .then((d) => active && setData(d))
      .catch(() => active && setError("Couldn't reach the PaperWeave server. Try again in a minute."));
    return () => {
      active = false;
    };
  }, [field]);

  if (error) return <p className="mt-8 text-sm text-muted">{error}</p>;
  if (!data) return <p className="mt-8 text-sm text-muted">Loading trends…</p>;

  const growing = data.topics.filter((t) => t.growth !== null);
  const [r0, r1] = data.recent_years;
  const [e0, e1] = data.earlier_years;

  return (
    <div className="mt-8 grid gap-10 lg:grid-cols-2">
      <section id="growing" className="scroll-mt-20 lg:col-span-2">
        <h2 className="font-serif text-2xl font-semibold">Which topics are growing</h2>
        <p className="mt-1 text-sm text-muted">
          Papers published per year across all of Semantic Scholar: the last 2 complete years vs the 2 before.
        </p>
        {growing.length ? <GrowthBars topics={growing} /> : <Empty />}
      </section>

      <section id="methods" className="scroll-mt-20">
        <h2 className="font-serif text-2xl font-semibold">Methods on the rise</h2>
        <p className="mt-1 text-sm text-muted">
          Share of papers in the library that propose or use each method: {r0}–{r1} vs {e0}–{e1}.
        </p>
        {data.rising_methods.length ? <MethodShares methods={data.rising_methods} /> : <Empty />}
      </section>

      <section id="breakout" className="scroll-mt-20">
        <h2 className="font-serif text-2xl font-semibold">Breakout papers</h2>
        <p className="mt-1 text-sm text-muted">Papers from {r0}–{r1} gaining citations fastest (citations per year).</p>
        {data.breakout_papers.length ? (
          <ol className="mt-4 space-y-3">
            {data.breakout_papers.map((p, i) => (
              <li key={p.arxiv_id} className="flex gap-3 text-sm">
                <span className="font-serif text-lg text-muted tabular-nums">{i + 1}</span>
                <div>
                  <Link href={`/paper/${p.arxiv_id}`} className="font-medium hover:text-accent">
                    {p.title}
                  </Link>
                  <div className="text-xs text-muted">
                    {p.year} · {p.citations.toLocaleString()} citations · ~{Math.round(p.per_year).toLocaleString()}/year
                  </div>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <Empty />
        )}
      </section>
    </div>
  );
}

function Empty() {
  return <p className="mt-4 text-sm text-muted">Not enough data here yet.</p>;
}

/** Diverging bars around zero: blue = growing, vermilion = shrinking; the signed label repeats it. */
function GrowthBars({ topics }: { topics: Trends["topics"] }) {
  const max = Math.max(...topics.map((t) => Math.abs(t.growth ?? 0)), 0.01);
  return (
    <ul className="mt-4 space-y-1.5">
      {topics.map((t) => {
        const g = t.growth ?? 0;
        const width = `${(Math.abs(g) / max) * 50}%`;
        return (
          <li
            key={t.topic}
            className="group grid grid-cols-[minmax(0,11rem)_minmax(0,1fr)_3.5rem] items-center gap-3 rounded px-1 text-sm hover:bg-accent-soft sm:grid-cols-[minmax(0,15rem)_minmax(0,1fr)_3.5rem]"
            title={`${t.topic} (${t.field}): ${pct(g)} · ${t.papers} papers in the library`}
          >
            <span className="truncate">{t.topic}</span>
            <span className="relative h-3">
              <span aria-hidden className="absolute inset-y-[-3px] left-1/2 w-px bg-border" />
              <span
                aria-hidden
                className={`absolute inset-y-0 rounded-sm ${g >= 0 ? "left-1/2 bg-rise" : "right-1/2 bg-fall"}`}
                style={{ width }}
              />
            </span>
            <span className="text-right tabular-nums text-muted group-hover:text-foreground">{pct(g)}</span>
          </li>
        );
      })}
    </ul>
  );
}

/** Bar = recent share; tick = earlier share, so the gap shows the change. */
function MethodShares({ methods }: { methods: Trends["rising_methods"] }) {
  const max = Math.max(...methods.flatMap((m) => [m.share_recent, m.share_earlier]), 0.001);
  return (
    <div className="mt-4">
      <div className="mb-2 flex gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-4 rounded-sm bg-rise" /> recent share
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-0.5 bg-foreground" /> earlier share
        </span>
      </div>
      <ul className="space-y-1.5">
        {methods.map((m) => (
          <li
            key={m.method}
            className="group grid grid-cols-[minmax(0,9rem)_minmax(0,1fr)_4.5rem] items-center gap-3 rounded px-1 text-sm hover:bg-accent-soft"
            title={`${m.method}: ${share(m.share_earlier)} → ${share(m.share_recent)} (${m.recent_papers} recent papers)`}
          >
            <span className="truncate">{m.method}</span>
            <span className="relative h-3">
              <span aria-hidden className="absolute inset-y-0 left-0 rounded-sm bg-rise" style={{ width: `${(m.share_recent / max) * 100}%` }} />
              <span
                aria-hidden
                className="absolute inset-y-[-3px] w-0.5 bg-foreground"
                style={{ left: `${(m.share_earlier / max) * 100}%` }}
              />
            </span>
            <span className="text-right tabular-nums text-muted group-hover:text-foreground">
              {m.change > 0 ? "+" : ""}
              {(m.change * 100).toFixed(1)} pts
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
