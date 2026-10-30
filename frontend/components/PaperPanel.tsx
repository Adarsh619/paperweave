"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getPaper } from "@/lib/api";
import type { Citation, Paper } from "@/lib/types";

export function Chips({ label, items, color }: { label: string; items: string[]; color: string }) {
  if (!items.length) return null;
  return (
    <div className="mt-3">
      <div className="text-xs font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {items.map((i) => (
          <span key={i} className="rounded-full border border-border px-2 py-0.5 text-xs" style={{ color }}>
            {i}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Slide-over card for a cited paper. Live arXiv results aren't in the graph, so they get a link only. */
export default function PaperPanel({ citation, onClose }: { citation: Citation | null; onClose: () => void }) {
  // Keyed by paper, so opening another paper starts with fresh (empty) state.
  return citation ? <PaperCard key={citation.arxiv_id} citation={citation} onClose={onClose} /> : null;
}

function PaperCard({ citation, onClose }: { citation: Citation; onClose: () => void }) {
  const [paper, setPaper] = useState<Paper | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getPaper(citation.arxiv_id)
      .then((p) => active && setPaper(p))
      .catch((e: Error) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [citation.arxiv_id]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const absUrl = citation.abs_url ?? `https://arxiv.org/abs/${citation.arxiv_id}`;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <aside
        className="h-full w-full max-w-md overflow-y-auto bg-surface p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        aria-label="Paper details"
      >
        <button type="button" onClick={onClose} className="float-right text-sm text-muted hover:text-foreground">
          Close
        </button>
        <div className="font-mono text-xs text-accent">{citation.arxiv_id}</div>
        <h2 className="mt-1 text-lg font-semibold leading-snug">{paper?.title ?? citation.title}</h2>

        {!paper && !error && <p className="mt-4 text-sm text-muted">Loading…</p>}
        {error && (
          <p className="mt-4 text-sm text-muted">
            {citation.source === "live" ? "A live arXiv result, newer than the indexed corpus." : error}
          </p>
        )}

        {paper && (
          <>
            <p className="mt-1 text-sm text-muted">
              {paper.authors.slice(0, 6).join(", ")}
              {paper.authors.length > 6 ? " et al." : ""} · {paper.year}
              {paper.venue ? ` · ${paper.venue}` : ""}
            </p>
            <p className="mt-2 text-xs text-muted">
              {paper.citation_count?.toLocaleString()} citations · cited by {paper.cited_by_in_corpus} papers in the
              corpus · cites {paper.cites_in_corpus}
            </p>
            <p className="mt-4 text-sm leading-relaxed">{paper.abstract}</p>
            <Chips label="Proposes" items={paper.proposes} color="var(--method)" />
            <Chips label="Evaluated on" items={paper.datasets} color="var(--dataset)" />
            <Chips label="Tasks" items={paper.tasks} color="var(--task)" />
          </>
        )}

        <div className="mt-6 flex flex-wrap gap-3 text-sm">
          <a href={absUrl} target="_blank" rel="noreferrer" className="text-accent underline">
            arXiv page
          </a>
          <a
            href={`https://arxiv.org/pdf/${citation.arxiv_id}`}
            target="_blank"
            rel="noreferrer"
            className="text-accent underline"
          >
            PDF
          </a>
          {paper && (
            <Link href={`/paper/${citation.arxiv_id}`} className="text-accent underline">
              Paper graph
            </Link>
          )}
        </div>
      </aside>
    </div>
  );
}
