import type { Step } from "@/lib/types";

const LABELS: Record<string, string> = {
  plan: "Plan",
  graph: "Graph",
  search: "Search",
  live: "arXiv",
  check: "Check",
  rewrite: "Retry",
  answer: "Answer",
  subgraph: "Graph view",
};

export default function AgentSteps({ steps, running }: { steps: Step[]; running: boolean }) {
  if (!steps.length && !running) return null;
  return (
    <ol className="space-y-2 border-l border-border pl-4" aria-label="Agent steps">
      {steps.map((s, i) => (
        <li key={i} className="relative text-sm">
          <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full bg-accent" />
          <span className="mr-2 font-medium">{LABELS[s.node] ?? s.node}</span>
          <span className="text-muted">{s.message}</span>
        </li>
      ))}
      {running && (
        <li className="relative text-sm text-muted">
          <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 animate-pulse rounded-full bg-border" />
          Working…
        </li>
      )}
    </ol>
  );
}
