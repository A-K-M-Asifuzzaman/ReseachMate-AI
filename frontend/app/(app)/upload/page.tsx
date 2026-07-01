"use client";

import { useEffect, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { Document } from "@/lib/types";

export default function UploadPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function refresh() {
    try {
      const r = await api.listDocuments();
      setDocs(r.items);
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  // Poll while anything is still processing.
  useEffect(() => {
    const anyProcessing = docs.some(
      (d) => d.status === "processing" || d.status === "uploaded"
    );
    if (!anyProcessing) return;
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [docs]);

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError("");
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        if (!file.name.toLowerCase().endsWith(".pdf")) {
          setError("Only PDF files are supported.");
          continue;
        }
        await api.upload(file);
      }
      await refresh();
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl p-8">
      <PageHeader title="Upload papers" subtitle="Drop research PDFs to add them to your library." />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-12 text-center transition ${
          dragOver
            ? "border-brand-500 bg-brand-500/5"
            : "border-slate-300 hover:border-brand-500 dark:border-ink-600"
        }`}
      >
        <UploadCloud className="mb-3 text-brand-500" size={40} />
        <p className="font-medium">
          {uploading ? "Uploading…" : "Drop PDFs here or click to browse"}
        </p>
        <p className="mt-1 text-sm text-slate-500">PDF only · up to 50 MB each</p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      {docs.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-lg font-semibold">Your papers</h2>
          <div className="space-y-2">
            {docs.map((d) => (
              <div key={d.id} className="card flex items-center justify-between py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">{d.title}</p>
                  <p className="truncate text-xs text-slate-500">
                    {d.num_pages ? `${d.num_pages} pages · ` : ""}
                    {d.num_chunks} chunks
                    {d.error ? ` · ${d.error}` : ""}
                  </p>
                </div>
                <StatusBadge status={d.status} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
