export type Step = { node: string; message: string };

export type Citation = {
  arxiv_id: string;
  title: string;
  year: number | null;
  abs_url: string | null;
  source: "graph" | "entity" | "search" | "live" | string;
};

export type NodeType = "Paper" | "Method" | "Dataset" | "Task";

export type GraphNode = {
  id: string;
  type: NodeType;
  label: string;
  arxiv_id?: string;
  year?: number | null;
};

export type GraphLink = { source: string; target: string; type: string };

export type Subgraph = { nodes: GraphNode[]; links: GraphLink[] };

/** Events streamed by POST /api/chat (and stored in examples.json). */
export type ChatEvent =
  | { event: "step"; data: Step }
  | { event: "token"; data: { text: string } }
  | { event: "answer"; data: { text: string } }
  | { event: "citations"; data: Citation[] }
  | { event: "subgraph"; data: Subgraph }
  | { event: "error"; data: { message: string } }
  | { event: "done"; data: { cached: boolean } };

export type Example = { question: string; events: ChatEvent[] };

/** An earlier question and its answer, sent with follow-ups (POST /api/chat "history"). */
export type Turn = { question: string; answer: string };

export type ExamplesFile = { generated: string; model: string; examples: Example[] };

/** frontend/public/stats.json, written by pipeline/export_stats.py. */
export type CoverageStats = {
  totals: { papers: number; citations: number; entities: number };
  fields: { name: string; papers: number; topics: { name: string; papers: number }[] }[];
};

/** GET /api/trends: data-driven, no forecasts. */
export type Trends = {
  field: string | null;
  recent_years: [number, number];
  earlier_years: [number, number];
  topics: { topic: string; field: string; papers: number; growth: number | null }[];
  rising_methods: {
    method: string;
    recent_papers: number;
    share_recent: number;
    share_earlier: number;
    change: number;
  }[];
  breakout_papers: { arxiv_id: string; title: string; year: number; citations: number; per_year: number }[];
};

export type Paper = {
  arxiv_id: string;
  title: string;
  abstract: string;
  year: number | null;
  venue: string | null;
  citation_count: number | null;
  abs_url: string;
  pdf_url: string;
  authors: string[];
  proposes: string[];
  datasets: string[];
  tasks: string[];
  cites_in_corpus: number;
  cited_by_in_corpus: number;
};
