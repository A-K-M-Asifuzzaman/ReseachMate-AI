"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Sparkles } from "lucide-react";
import { ForceGraph } from "@/components/ForceGraph";
import { PageHeader } from "@/components/PageHeader";
import { api } from "@/lib/api";
import type { Document, GraphResponse } from "@/lib/types";

function GraphInner() {
  const searchParams = useSearchParams();
  const [docs, setDocs] = useState<Document[]>([]);
  const [scope, setScope] = useState<string>("all"); // "all" | documentId
  const [graph, setGraph] = useState<GraphResponse>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);

  useEffect(() => {
    api.listDocuments().then((r) => {
      setDocs(r.items.filter((d) => d.status === "ready"));
      const preselect = searchParams.get("doc");
      if (preselect) setScope(preselect);
    });
  }, [searchParams]);

  async function loadGraph(currentScope = scope) {
    setLoading(true);
    try {
      const g =
        currentScope === "all"
          ? await api.userGraph()
          : await api.documentGraph(currentScope);
      setGraph(g);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadGraph(scope);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope]);

  async function extract() {
    if (scope === "all") return;
    setExtracting(true);
    try {
      await api.extractGraph(scope);
      await loadGraph(scope);
    } finally {
      setExtracting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-8">
      <PageHeader
        title="Knowledge graph"
        subtitle="Entities and relations extracted from your papers."
        action={
          scope !== "all" ? (
            <button onClick={extract} disabled={extracting} className="btn-primary">
              <Sparkles size={16} />
              {extracting ? "Extracting…" : "Extract entities"}
            </button>
          ) : undefined
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <select
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          className="input max-w-xs"
        >
          <option value="all">Whole library</option>
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.title}
            </option>
          ))}
        </select>
        <span className="text-sm text-slate-500">
          {graph.nodes.length} entities · {graph.edges.length} relations
        </span>
      </div>

      {loading ? (
        <div className="flex h-96 items-center justify-center text-sm text-slate-500">
          Loading graph…
        </div>
      ) : (
        <ForceGraph nodes={graph.nodes} edges={graph.edges} />
      )}
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-slate-500">Loading graph…</div>}>
      <GraphInner />
    </Suspense>
  );
}
