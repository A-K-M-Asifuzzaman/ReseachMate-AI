import type { DocumentStatus } from "@/lib/types";

const styles: Record<DocumentStatus, string> = {
  ready: "bg-emerald-500/15 text-emerald-500",
  processing: "bg-amber-500/15 text-amber-500",
  uploaded: "bg-slate-500/15 text-slate-400",
  failed: "bg-red-500/15 text-red-500",
};

const labels: Record<DocumentStatus, string> = {
  ready: "Ready",
  processing: "Processing…",
  uploaded: "Queued",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {status === "processing" && (
        <span className="mr-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {labels[status]}
    </span>
  );
}
