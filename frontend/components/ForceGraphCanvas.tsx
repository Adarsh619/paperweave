"use client";

// Loaded only in the browser (GraphView imports it with ssr: false): the library needs `window`.
import { useEffect, useRef, useState } from "react";
import ForceGraph2D, { type ForceGraphMethods } from "react-force-graph-2d";

import type { GraphLink, GraphNode } from "@/lib/types";

type PositionedNode = GraphNode & { x?: number; y?: number };

function shorten(label: string, max = 26) {
  return label.length > max ? label.slice(0, max - 1) + "…" : label;
}

export default function ForceGraphCanvas({
  nodes,
  links,
  width,
  height,
  colors,
  onPaper,
}: {
  nodes: GraphNode[];
  links: GraphLink[];
  width: number;
  height: number;
  colors: Record<string, string>;
  onPaper?: (arxivId: string) => void;
}) {
  const graph = useRef<ForceGraphMethods | undefined>(undefined);
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    // Spread nodes out: the defaults pack 20+ nodes into an unreadable clump.
    graph.current?.d3Force("charge")?.strength(-160);
    graph.current?.d3Force("link")?.distance(55);
    graph.current?.d3ReheatSimulation();
  }, [nodes]);

  return (
    <ForceGraph2D
      ref={graph}
      graphData={{ nodes, links }}
      width={width}
      height={height}
      cooldownTicks={150}
      onEngineStop={() => graph.current?.zoomToFit(400, 30)}
      linkColor={() => colors.link}
      linkDirectionalArrowLength={3}
      linkDirectionalArrowRelPos={1}
      nodeLabel={(node) => (node as PositionedNode).label}
      onNodeHover={(node) => setHovered(node ? String((node as PositionedNode).id) : null)}
      onNodeClick={(node) => {
        const n = node as PositionedNode;
        if (n.type === "Paper" && n.arxiv_id) onPaper?.(n.arxiv_id);
      }}
      nodeCanvasObject={(node, ctx, scale) => {
        const n = node as PositionedNode;
        if (n.x === undefined || n.y === undefined) return;
        const r = n.type === "Paper" ? 6 : 4.5;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, 2 * Math.PI);
        ctx.fillStyle = colors[n.type] ?? "#888";
        ctx.fill();
        // Paper titles are long: show them when zoomed in or hovered; entity names always.
        if (n.type !== "Paper" || scale > 2.2 || hovered === n.id) {
          ctx.font = `${11 / scale}px sans-serif`;
          ctx.fillStyle = colors.text;
          ctx.textAlign = "center";
          ctx.fillText(shorten(n.label), n.x, n.y + r + 10 / scale);
        }
      }}
      nodePointerAreaPaint={(node, color, ctx) => {
        const n = node as PositionedNode;
        if (n.x === undefined || n.y === undefined) return;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(n.x, n.y, 8, 0, 2 * Math.PI);
        ctx.fill();
      }}
    />
  );
}
