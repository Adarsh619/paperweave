"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { getTrends } from "@/lib/api";
import { askHref, EXAMPLE_QUESTIONS } from "@/lib/examples";
import { useRecent } from "@/lib/recent";
import type { CoverageStats, Trends } from "@/lib/types";
import coverage from "@/public/stats.json";

const stats = coverage as CoverageStats;

/** Wide screens only: a page with sticky side columns. Below xl the sidebars are hidden and the page is unchanged. */
export function WithSidebars({ left, right, children }: { left?: ReactNode; right?: ReactNode; children: ReactNode }) {
  const cols = left && right ? "xl:grid-cols-[11rem_minmax(0,1fr)_14rem]" : left ? "xl:grid-cols-[14rem_minmax(0,1fr)]" : "xl:grid-cols-[minmax(0,1fr)_14rem]";
  return (
    <div className={`mx-auto max-w-[88rem] xl:grid xl:gap-8 xl:px-4 ${cols}`}>
      {left && <Side>{left}</Side>}
      <div className="min-w-0">{children}</div>
      {right && <Side>{right}</Side>}
    </div>
  );
}

function Side({ children }: { children: ReactNode }) {
  return (
    <aside className="hidden xl:block">
      <div className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto py-8 pr-1">{children}</div>
    </aside>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className="mb-2 px-2 text-[11px] font-medium uppercase tracking-[0.15em] text-muted">{title}</h2>
      {children}
    </section>
  );
}

const itemClass = "block truncate rounded-md px-2 py-1.5 transition-colors hover:bg-accent-soft hover:text-foreground";

/** New question, this visitor's recent questions, and the example questions. */
export function QuestionRail({ current }: { current?: string }) {
  const recent = useRecent();
  const link = (q: string) => (
    <li key={q}>
      <Link
        href={askHref(q)}
        title={q}
        aria-current={q === current ? "page" : undefined}
        className={`${itemClass} ${q === current ? "bg-accent-soft text-foreground" : "text-muted"}`}
      >
        {q}
      </Link>
    </li>
  );
  return (
    <nav aria-label="Questions" className="space-y-6 text-sm">
      <Link
        href="/"
        className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 font-medium transition-colors hover:border-accent"
      >
        <span aria-hidden className="text-accent">+</span> New question
      </Link>
      {recent.length > 0 && (
        <Group title="Recent">
          <ul>{recent.map(link)}</ul>
        </Group>
      )}
      <Group title="Examples (instant)">
        <ul>{EXAMPLE_QUESTIONS.map(link)}</ul>
      </Group>
    </nav>
  );
}

const pct = (x: number) => `${x > 0 ? "+" : ""}${Math.round(x * 100)}%`;

/** What's in the library, and which topics are growing fastest. */
export function LibraryPanel() {
  const [rising, setRising] = useState<Trends["topics"] | null>(null);
  useEffect(() => {
    let active = true;
    getTrends()
      .then((d) => active && setRising(d.topics.filter((t) => (t.growth ?? 0) > 0).slice(0, 5)))
      .catch(() => active && setRising([]));
    return () => {
      active = false;
    };
  }, []);

  const { totals } = stats;
  return (
    <div className="space-y-6 text-sm">
      <Group title="The library">
        <dl className="space-y-1 px-2">
          {[
            [totals.papers, "papers"],
            [totals.citations, "citation links"],
            [totals.entities, "methods, datasets & tasks"],
          ].map(([n, label]) => (
            <div key={label} className="flex items-baseline justify-between gap-2">
              <dt className="text-muted">{label}</dt>
              <dd className="font-serif font-semibold tabular-nums">{n.toLocaleString()}</dd>
            </div>
          ))}
        </dl>
      </Group>
      <Group title="Fields">
        <ul className="space-y-1 px-2">
          {stats.fields.map((f) => (
            <li key={f.name} className="flex items-baseline justify-between gap-2">
              <span className="truncate text-muted" title={f.name}>
                {f.name}
              </span>
              <span className="tabular-nums">{f.papers.toLocaleString()}</span>
            </li>
          ))}
        </ul>
      </Group>
      {rising?.length !== 0 && (
        <Group title="Growing fastest">
          {rising ? (
            <ul className="space-y-1 px-2">
              {rising.map((t) => (
                <li key={t.topic} className="flex items-baseline justify-between gap-2" title={`${t.topic} (${t.field})`}>
                  <span className="truncate text-muted">{t.topic}</span>
                  <span className="tabular-nums text-rise">{pct(t.growth ?? 0)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-2 text-muted">Loading…</p>
          )}
          <Link href="/trends" className="mt-2 block px-2 text-accent hover:underline">
            See all trends →
          </Link>
        </Group>
      )}
    </div>
  );
}

/** "On this page" links to the page's sections. */
export function PageOutline({ items }: { items: [id: string, label: string][] }) {
  return (
    <nav aria-label="On this page" className="text-sm">
      <Group title="On this page">
        <ul className="border-l border-border">
          {items.map(([id, label]) => (
            <li key={id}>
              <a href={`#${id}`} className="-ml-px block border-l border-transparent py-1.5 pl-3 text-muted transition-colors hover:border-accent hover:text-foreground">
                {label}
              </a>
            </li>
          ))}
        </ul>
      </Group>
    </nav>
  );
}
