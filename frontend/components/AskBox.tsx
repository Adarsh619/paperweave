"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { askHref } from "@/lib/examples";

export default function AskBox({ initial = "", autoFocus = false }: { initial?: string; autoFocus?: boolean }) {
  const router = useRouter();
  const [question, setQuestion] = useState(initial);
  const valid = question.trim().length >= 3;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) router.push(askHref(question));
      }}
      className="flex w-full gap-2"
    >
      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        maxLength={500}
        autoFocus={autoFocus}
        placeholder="Ask about AI research, e.g. What improved on RAG?"
        aria-label="Your question"
        className="min-w-0 flex-1 rounded-lg border border-border bg-surface px-4 py-3 text-base outline-none focus:border-accent"
      />
      <button
        type="submit"
        disabled={!valid}
        className="rounded-lg bg-accent px-5 py-3 font-medium text-white disabled:opacity-40"
      >
        Ask
      </button>
    </form>
  );
}
