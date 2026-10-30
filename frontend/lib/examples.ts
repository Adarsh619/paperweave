import type { Example, ExamplesFile } from "./types";

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

export async function findExample(question: string): Promise<Example | null> {
  const file = await loadExamples();
  const key = normalize(question);
  return file?.examples.find((e) => normalize(e.question) === key) ?? null;
}
