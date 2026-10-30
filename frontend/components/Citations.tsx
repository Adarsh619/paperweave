import type { Citation } from "@/lib/types";

export default function Citations({ items, onOpen }: { items: Citation[]; onOpen: (c: Citation) => void }) {
  if (!items.length) return null;
  return (
    <section>
      <h2 className="text-sm font-medium uppercase tracking-wide text-muted">Sources</h2>
      <ul className="mt-2 space-y-1.5">
        {items.map((c) => (
          <li key={c.arxiv_id} className="text-sm">
            <button type="button" onClick={() => onOpen(c)} className="text-left hover:text-accent">
              <span className="mr-2 font-mono text-xs text-accent">{c.arxiv_id}</span>
              {c.title}
              {c.year ? <span className="text-muted"> ({c.year})</span> : null}
              {c.source === "live" && (
                <span className="ml-2 rounded bg-accent-soft px-1.5 py-0.5 text-xs text-accent">live arXiv</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
