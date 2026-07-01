"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  FileText,
  MessagesSquare,
  Upload as UploadIcon,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Document } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listDocuments()
      .then((r) => setDocs(r.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const ready = docs.filter((d) => d.status === "ready").length;
  const processing = docs.filter((d) => d.status === "processing").length;

  const stats = [
    { label: "Papers", value: docs.length },
    { label: "Ready", value: ready },
    { label: "Processing", value: processing },
  ];

  return (
    <div className="mx-auto max-w-5xl p-8">
      <PageHeader
        title={`Welcome back, ${user?.name?.split(" ")[0] ?? "researcher"}`}
        subtitle="Your AI research workspace."
      />

      <div className="mb-8 grid grid-cols-3 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="card">
            <p className="text-3xl font-semibold">{s.value}</p>
            <p className="text-sm text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <Link href="/upload" className="card group flex items-center justify-between hover:border-brand-500">
          <div className="flex items-center gap-3">
            <UploadIcon className="text-brand-500" size={20} />
            <span className="font-medium">Upload a paper</span>
          </div>
          <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-1 transition" />
        </Link>
        <Link href="/chat" className="card group flex items-center justify-between hover:border-brand-500">
          <div className="flex items-center gap-3">
            <MessagesSquare className="text-brand-500" size={20} />
            <span className="font-medium">Ask a question</span>
          </div>
          <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-1 transition" />
        </Link>
        <Link href="/library" className="card group flex items-center justify-between hover:border-brand-500">
          <div className="flex items-center gap-3">
            <FileText className="text-brand-500" size={20} />
            <span className="font-medium">Browse library</span>
          </div>
          <ArrowRight size={16} className="text-slate-400 group-hover:translate-x-1 transition" />
        </Link>
      </div>

      <h2 className="mb-3 text-lg font-semibold">Recent papers</h2>
      {loading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : docs.length === 0 ? (
        <div className="card text-center text-sm text-slate-500">
          No papers yet.{" "}
          <Link href="/upload" className="text-brand-500 hover:underline">
            Upload your first PDF
          </Link>
          .
        </div>
      ) : (
        <div className="space-y-2">
          {docs.slice(0, 5).map((d) => (
            <div key={d.id} className="card flex items-center justify-between py-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{d.title}</p>
                <p className="truncate text-xs text-slate-500">
                  {d.authors || "Unknown authors"}
                  {d.year ? ` · ${d.year}` : ""} · {d.num_chunks} chunks
                </p>
              </div>
              <StatusBadge status={d.status} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
