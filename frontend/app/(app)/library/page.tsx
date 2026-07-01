"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { GitGraph, MessagesSquare, ScrollText, Trash2 } from "lucide-react";
import { Markdown } from "@/components/Markdown";
import { Modal } from "@/components/Modal";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type {
  ComparisonResponse,
  Document,
  SummaryResponse,
} from "@/lib/types";

export default function LibraryPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const [summaryDoc, setSummaryDoc] = useState<Document | null>(null);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [comparing, setComparing] = useState(false);

  async function refresh() {
    const r = await api.listDocuments();
    setDocs(r.items);
    setLoading(false);
  }
  useEffect(() => {
    refresh();
  }, []);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  async function openSummary(doc: Document, type: "short" | "detailed") {
    setSummaryDoc(doc);
    setSummary(null);
    setSummaryLoading(true);
    try {
      setSummary(await api.summarize(doc.id, type));
    } finally {
      setSummaryLoading(false);
    }
  }

  async function runComparison() {
    setComparing(true);
    setComparison(null);
    try {
      setComparison(await api.compare(Array.from(selected)));
    } finally {
      setComparing(false);
    }
  }

  async function remove(id: string) {
    if (!confirm("Delete this paper and all its data?")) return;
    await api.deleteDocument(id);
    setSelected((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
    refresh();
  }

  return (
    <div className="mx-auto max-w-5xl p-8">
      <PageHeader
        title="Paper library"
        subtitle="Summarize, compare, and manage your uploaded papers."
        action={
          selected.size >= 2 ? (
            <button onClick={runComparison} className="btn-primary">
              Compare {selected.size} papers
            </button>
          ) : undefined
        }
      />

      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : docs.length === 0 ? (
        <div className="card text-center text-sm text-slate-500">
          No papers yet.{" "}
          <Link href="/upload" className="text-brand-500 hover:underline">
            Upload one
          </Link>
          .
        </div>
      ) : (
        <div className="space-y-3">
          {docs.map((d) => (
            <div key={d.id} className="card">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={selected.has(d.id)}
                  onChange={() => toggle(d.id)}
                  disabled={d.status !== "ready"}
                  className="mt-1.5 h-4 w-4 accent-brand-600"
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="truncate font-medium">{d.title}</p>
                    <StatusBadge status={d.status} />
                  </div>
                  <p className="mt-0.5 truncate text-xs text-slate-500">
                    {d.authors || "Unknown authors"}
                    {d.year ? ` · ${d.year}` : ""}
                    {d.num_pages ? ` · ${d.num_pages} pages` : ""} · {d.num_chunks} chunks
                  </p>
                  {d.abstract && (
                    <p className="mt-2 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
                      {d.abstract}
                    </p>
                  )}

                  {d.status === "ready" && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button onClick={() => openSummary(d, "short")} className="btn-ghost !px-3 !py-1 text-xs">
                        <ScrollText size={14} /> Summary
                      </button>
                      <Link href={`/chat?doc=${d.id}`} className="btn-ghost !px-3 !py-1 text-xs">
                        <MessagesSquare size={14} /> Ask
                      </Link>
                      <Link href={`/graph?doc=${d.id}`} className="btn-ghost !px-3 !py-1 text-xs">
                        <GitGraph size={14} /> Graph
                      </Link>
                      <button
                        onClick={() => remove(d.id)}
                        className="btn-ghost !px-3 !py-1 text-xs text-red-500"
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary modal */}
      <Modal
        open={!!summaryDoc}
        onClose={() => setSummaryDoc(null)}
        title={summaryDoc?.title ?? "Summary"}
      >
        {summaryDoc && (
          <div>
            <div className="mb-4 flex gap-2">
              <button onClick={() => openSummary(summaryDoc, "short")} className="btn-ghost text-xs">
                Short
              </button>
              <button onClick={() => openSummary(summaryDoc, "detailed")} className="btn-ghost text-xs">
                Detailed
              </button>
            </div>
            {summaryLoading && <p className="text-sm text-slate-500">Generating…</p>}
            {summary?.short_summary && <Markdown>{summary.short_summary}</Markdown>}
            {summary?.detailed_summary && (
              <div className="space-y-3 text-sm">
                {Object.entries(summary.detailed_summary).map(([k, v]) =>
                  v ? (
                    <div key={k}>
                      <p className="font-semibold capitalize">{k}</p>
                      <p className="text-slate-500 dark:text-slate-400">{v}</p>
                    </div>
                  ) : null
                )}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Comparison modal */}
      <Modal open={comparing || !!comparison} onClose={() => setComparison(null)} title="Paper comparison" wide>
        {comparing && <p className="text-sm text-slate-500">Comparing papers…</p>}
        {comparison && (
          <div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr>
                    <th className="border-b border-slate-200 p-2 text-left dark:border-ink-700">Dimension</th>
                    {comparison.papers.map((p) => (
                      <th key={p.document_id} className="border-b border-slate-200 p-2 text-left dark:border-ink-700">
                        {p.title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comparison.rows.map((row) => (
                    <tr key={row.dimension} className="align-top">
                      <td className="border-b border-slate-100 p-2 font-medium dark:border-ink-700/50">
                        {row.dimension}
                      </td>
                      {comparison.papers.map((p) => (
                        <td key={p.document_id} className="border-b border-slate-100 p-2 text-slate-500 dark:border-ink-700/50 dark:text-slate-400">
                          {row.cells[p.document_id] || "—"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {comparison.synthesis && (
              <div className="mt-4 rounded-lg bg-brand-500/10 p-3 text-sm">
                <span className="font-semibold">Synthesis. </span>
                {comparison.synthesis}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
