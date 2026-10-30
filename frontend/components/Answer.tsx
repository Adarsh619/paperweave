"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const CITATION = /\[(\d{4}\.\d{4,5}(?:\s*,\s*\d{4}\.\d{4,5})*)\]/g;

/** "[2005.11401, 2404.16130]" -> "[[2005.11401](#cite-2005.11401), ...]" so each ID is a link. */
function linkCitations(text: string) {
  return text.replace(CITATION, (_, ids: string) =>
    "[" + ids.split(/\s*,\s*/).map((id) => `[${id}](#cite-${id})`).join(", ") + "]",
  );
}

export default function Answer({ text, onCite }: { text: string; onCite: (arxivId: string) => void }) {
  return (
    <div className="prose-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Wide comparison tables scroll on their own instead of widening the page on phones.
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table>{children}</table>
            </div>
          ),
          a: ({ href, children }) => {
            if (href?.startsWith("#cite-")) {
              const id = href.slice(6);
              return (
                <button
                  type="button"
                  onClick={() => onCite(id)}
                  className="rounded bg-accent-soft px-1 font-mono text-[0.8em] text-accent hover:underline"
                >
                  {children}
                </button>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" className="text-accent underline">
                {children}
              </a>
            );
          },
        }}
      >
        {linkCitations(text)}
      </ReactMarkdown>
    </div>
  );
}
