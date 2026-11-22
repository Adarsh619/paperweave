import type { Citation, Example, ExamplesFile, Step, Subgraph } from "./types";

/** Keep in sync with backend/scripts/export_examples.py, which saves their answers. */
export const EXAMPLE_QUESTIONS = [
  "What improved on RAG, and which datasets did those papers use?",
  "Compare GraphRAG, RAPTOR and HippoRAG",
  "Which papers in the corpus build on Attention Is All You Need?",
  "Compare Self-RAG and Corrective RAG",
  "Which papers evaluate on HotpotQA, and what do they propose?",
  "What are the most cited papers on hallucination since 2023?",
  "How does HyDE improve zero-shot dense retrieval?",
  "What are the latest papers on agent memory?",
  "Compare ReAct and Reflexion",
  "Which authors wrote the most papers in the corpus?",
  "How do physics-informed neural networks work?",
  "What is trending in quantum computing?",
];

export const askHref = (question: string) => `/ask?q=${encodeURIComponent(question.trim())}`;

// Same rule as the backend cache (app/cache.py), so "what is rag?" matches "What is RAG".
export const normalize = (q: string) =>
  q.toLowerCase().replace(/\s+/g, " ").replace(/^[\s?.!]+|[\s?.!]+$/g, "");

let examples: Promise<ExamplesFile | null> | null = null;

export function loadExamples(): Promise<ExamplesFile | null> {
  examples ??= fetch("/examples.json")
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
  return examples;
}

/** A saved example's events folded into the finished answer (for the home page preview). */
export function finishedAnswer(example: Example) {
  const result = { steps: [] as Step[], text: "", citations: [] as Citation[], graph: { nodes: [], links: [] } as Subgraph };
  for (const e of example.events) {
    if (e.event === "step") result.steps.push(e.data);
    else if (e.event === "answer") result.text = e.data.text;
    else if (e.event === "citations") result.citations = e.data;
    else if (e.event === "subgraph") result.graph = e.data;
  }
  return result;
}

export async function findExample(question: string): Promise<Example | null> {
  const file = await loadExamples();
  const key = normalize(question);
  return file?.examples.find((e) => normalize(e.question) === key) ?? null;
}
