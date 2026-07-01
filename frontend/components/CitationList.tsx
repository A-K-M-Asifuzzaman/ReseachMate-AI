import { FileText } from "lucide-react";
import type { Citation } from "@/lib/types";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        Sources
      </p>
      {citations.map((c, i) => (
        <div
          key={c.chunk_id}
          className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs dark:border-ink-700 dark:bg-ink-900/50"
        >
          <div className="mb-1 flex items-center gap-2 font-medium">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-brand-500/15 text-brand-500">
              {i + 1}
            </span>
            <FileText size={13} className="text-slate-400" />
            <span className="truncate">{c.title}</span>
          </div>
          <p className="mb-1 text-slate-500">
            {c.page_number != null && `p.${c.page_number}`}
            {c.section && ` · ${c.section}`}
            {" · "}score {c.score.toFixed(3)}
          </p>
          <p className="line-clamp-3 text-slate-500 dark:text-slate-400">{c.snippet}</p>
        </div>
      ))}
    </div>
  );
}
