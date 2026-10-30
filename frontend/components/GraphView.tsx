"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

import type { NodeType, Subgraph } from "@/lib/types";

// The force graph draws on a canvas and needs `window`, so it only loads in the browser.
const ForceGraphCanvas = dynamic(() => import("./ForceGraphCanvas"), { ssr: false });

const COLOR_VARS: Record<NodeType, string> = {
  Paper: "--paper",
  Method: "--method",
  Dataset: "--dataset",
  Task: "--task",
};

function cssVar(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";
}

export default function GraphView({
  graph,
  onPaper,
  height = 420,
}: {
  graph: Subgraph;
  onPaper?: (arxivId: string) => void;
  height?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [colors, setColors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!box.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(box.current);
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const readColors = () =>
      setColors({
        ...Object.fromEntries(Object.entries(COLOR_VARS).map(([type, v]) => [type, cssVar(v)])),
        text: cssVar("--foreground"),
        link: cssVar("--border"),
      });
    readColors();
    media.addEventListener("change", readColors);
    return () => {
      observer.disconnect();
      media.removeEventListener("change", readColors);
    };
  }, []);

  // The graph library mutates nodes and links (adds x/y, replaces ids with objects); give it copies.
  const data = useMemo(
    () => ({ nodes: graph.nodes.map((n) => ({ ...n })), links: graph.links.map((l) => ({ ...l })) }),
    [graph],
  );

  const present = new Set(graph.nodes.map((n) => n.type));

  return (
    <div>
      <div ref={box} className="overflow-hidden rounded-lg border border-border bg-surface" style={{ height }}>
        {width > 0 && graph.nodes.length > 0 && (
          <ForceGraphCanvas
            nodes={data.nodes}
            links={data.links}
            width={width}
            height={height}
            colors={colors}
            onPaper={onPaper}
          />
        )}
        {graph.nodes.length === 0 && <p className="p-6 text-sm text-muted">No graph for this answer.</p>}
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
        {(Object.keys(COLOR_VARS) as NodeType[])
          .filter((t) => present.has(t))
          .map((t) => (
            <span key={t} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: colors[t] }} />
              {t}
            </span>
          ))}
        <span>· hover for titles, scroll to zoom{onPaper && present.has("Paper") ? ", click a paper to open it" : ""}</span>
      </div>
    </div>
  );
}
