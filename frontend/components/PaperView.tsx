"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import GraphView from "@/components/GraphView";
import { Chips } from "@/components/PaperPanel";
import { getPaper, getPaperGraph } from "@/lib/api";
import type { Paper, Subgraph } from "@/lib/types";

export default function PaperView() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [paper, setPaper] = useState<Paper | null>(null);
  const [graph, setGraph] = useState<Subgraph | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getPaper(id), getPaperGraph(id)])
      .then(([p, g]) => {
        if (!active) return;
        setPaper(p);
        setGraph(g);
      })
      .catch((e: Error) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [id]);

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <p className="text-sm">
          {error}.{" "}
          <a href={`https://arxiv.org/abs/${id}`} className="text-accent underline" target="_blank" rel="noreferrer">
            Open {id} on arXiv
          </a>
        </p>
      </div>
    );
  }
  if (!paper || !graph) {
    return <div className="mx-auto max-w-4xl px-4 py-10 text-sm text-muted">Loading paper {id}… (the server may be waking up)</div>;
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
        <article className="min-w-0">
          <div className="font-mono text-xs text-accent">{paper.arxiv_id}</div>
          <h1 className="mt-1 text-2xl font-semibold leading-snug">{paper.title}</h1>
          <p className="mt-2 text-sm text-muted">
            {paper.authors.slice(0, 8).join(", ")}
            {paper.authors.length > 8 ? " et al." : ""} · {paper.year}
            {paper.venue ? ` · ${paper.venue}` : ""}
          </p>
          <p className="mt-1 text-xs text-muted">
            {paper.citation_count?.toLocaleString()} citations · cited by {paper.cited_by_in_corpus} corpus papers ·
            cites {paper.cites_in_corpus}
          </p>
          <p className="mt-5 leading-relaxed">{paper.abstract}</p>
          <Chips label="Proposes" items={paper.proposes} color="var(--method)" />
          <Chips label="Evaluated on" items={paper.datasets} color="var(--dataset)" />
          <Chips label="Tasks" items={paper.tasks} color="var(--task)" />
          <div className="mt-6 flex gap-4 text-sm">
            <a href={paper.abs_url} className="text-accent underline" target="_blank" rel="noreferrer">
              arXiv page
            </a>
            <a href={paper.pdf_url} className="text-accent underline" target="_blank" rel="noreferrer">
              PDF
            </a>
          </div>
        </article>
        <aside className="min-w-0">
          <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-muted">Citations and entities</h2>
          <GraphView graph={graph} height={480} onPaper={(other) => other !== id && router.push(`/paper/${other}`)} />
        </aside>
      </div>
    </div>
  );
}
