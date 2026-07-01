"use client";

import { useMemo, useRef, useState } from "react";
import type { GraphEdge, GraphNode } from "@/lib/types";

const WIDTH = 820;
const HEIGHT = 560;

const TYPE_COLORS: Record<string, string> = {
  Concept: "#6366f1",
  Method: "#22c55e",
  Model: "#f59e0b",
  Dataset: "#06b6d4",
  Task: "#ec4899",
  Metric: "#a855f7",
  Tool: "#ef4444",
  Author: "#94a3b8",
};

interface Pos {
  x: number;
  y: number;
}

/** Compact Fruchterman-Reingold layout, computed once per data change. */
function layout(nodes: GraphNode[], edges: GraphEdge[]): Record<string, Pos> {
  const n = nodes.length || 1;
  const area = WIDTH * HEIGHT;
  const k = Math.sqrt(area / n);
  const pos: Record<string, Pos> = {};
  nodes.forEach((node, i) => {
    // Seed on a circle for a stable, non-random-looking start.
    const angle = (2 * Math.PI * i) / n;
    pos[node.id] = {
      x: WIDTH / 2 + (Math.cos(angle) * WIDTH) / 4,
      y: HEIGHT / 2 + (Math.sin(angle) * HEIGHT) / 4,
    };
  });

  let temp = WIDTH / 10;
  const iterations = 300;
  for (let it = 0; it < iterations; it++) {
    const disp: Record<string, Pos> = {};
    nodes.forEach((v) => (disp[v.id] = { x: 0, y: 0 }));

    // Repulsion between every pair.
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = pos[nodes[i].id];
        const b = pos[nodes[j].id];
        let dx = a.x - b.x;
        let dy = a.y - b.y;
        let dist = Math.hypot(dx, dy) || 0.01;
        const rep = (k * k) / dist;
        dx = (dx / dist) * rep;
        dy = (dy / dist) * rep;
        disp[nodes[i].id].x += dx;
        disp[nodes[i].id].y += dy;
        disp[nodes[j].id].x -= dx;
        disp[nodes[j].id].y -= dy;
      }
    }

    // Attraction along edges.
    for (const e of edges) {
      const a = pos[e.source];
      const b = pos[e.target];
      if (!a || !b) continue;
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      const dist = Math.hypot(dx, dy) || 0.01;
      const att = (dist * dist) / k;
      dx = (dx / dist) * att;
      dy = (dy / dist) * att;
      disp[e.source].x -= dx;
      disp[e.source].y -= dy;
      disp[e.target].x += dx;
      disp[e.target].y += dy;
    }

    // Apply displacement, bounded by temperature; keep inside the canvas.
    for (const v of nodes) {
      const d = disp[v.id];
      const dist = Math.hypot(d.x, d.y) || 0.01;
      pos[v.id].x += (d.x / dist) * Math.min(dist, temp);
      pos[v.id].y += (d.y / dist) * Math.min(dist, temp);
      pos[v.id].x = Math.max(30, Math.min(WIDTH - 30, pos[v.id].x));
      pos[v.id].y = Math.max(30, Math.min(HEIGHT - 30, pos[v.id].y));
    }
    temp *= 0.97; // cool down
  }
  return pos;
}

export function ForceGraph({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  const base = useMemo(() => layout(nodes, edges), [nodes, edges]);
  const [positions, setPositions] = useState<Record<string, Pos>>(base);
  const [hover, setHover] = useState<string | null>(null);
  const dragging = useRef<string | null>(null);

  // Reset positions when the computed layout changes.
  useMemo(() => setPositions(base), [base]);

  function onPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    if (!dragging.current) return;
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * WIDTH;
    const y = ((e.clientY - rect.top) / rect.height) * HEIGHT;
    setPositions((p) => ({ ...p, [dragging.current!]: { x, y } }));
  }

  const connected = (id: string) =>
    edges.some((e) => (e.source === id || e.target === id) && (e.source === hover || e.target === hover));

  if (!nodes.length) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-slate-500">
        No graph yet. Extract entities from a paper to build one.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white dark:border-ink-700 dark:bg-ink-800">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full touch-none"
        onPointerMove={onPointerMove}
        onPointerUp={() => (dragging.current = null)}
        onPointerLeave={() => (dragging.current = null)}
      >
        {edges.map((e, i) => {
          const a = positions[e.source];
          const b = positions[e.target];
          if (!a || !b) return null;
          const active = hover && (e.source === hover || e.target === hover);
          return (
            <g key={i}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={active ? "#6366f1" : "currentColor"}
                strokeOpacity={active ? 0.8 : 0.15}
                strokeWidth={active ? 1.5 : 1}
                className="text-slate-400"
              />
              {active && (
                <text
                  x={(a.x + b.x) / 2}
                  y={(a.y + b.y) / 2}
                  fontSize="9"
                  fill="#818cf8"
                  textAnchor="middle"
                >
                  {e.label}
                </text>
              )}
            </g>
          );
        })}

        {nodes.map((node) => {
          const p = positions[node.id];
          if (!p) return null;
          const r = 6 + Math.min(node.weight, 6) * 2;
          const dim = hover && hover !== node.id && !connected(node.id);
          const color = TYPE_COLORS[node.type] ?? "#6366f1";
          return (
            <g
              key={node.id}
              transform={`translate(${p.x},${p.y})`}
              opacity={dim ? 0.25 : 1}
              onPointerDown={() => (dragging.current = node.id)}
              onMouseEnter={() => setHover(node.id)}
              onMouseLeave={() => setHover(null)}
              className="cursor-grab"
            >
              <circle r={r} fill={color} />
              <text
                x={r + 3}
                y={4}
                fontSize="11"
                className="fill-slate-700 dark:fill-slate-200"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
