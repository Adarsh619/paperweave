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

export type ExamplesFile = { generated: string; model: string; examples: Example[] };

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
