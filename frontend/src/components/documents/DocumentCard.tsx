import { motion } from "framer-motion";
import { ExternalLink, FileText, Trash2 } from "lucide-react";
import { documentFileUrl } from "@/services/api";
import { cn, fileTypeLabel, formatBytes, formatDate } from "@/lib/utils";
import { fadeInUp } from "@/lib/motion";
import type { DocumentItem, DocumentStatus } from "@/types";

const STATUS_STYLES: Record<DocumentStatus, { dot: string; label: string; text: string }> = {
  completed: { dot: "bg-emerald-400", label: "Ready", text: "text-emerald-300" },
  processing: { dot: "bg-amber-400 animate-pulse", label: "Processing", text: "text-amber-300" },
  pending: { dot: "bg-slate-400", label: "Pending", text: "text-muted" },
  failed: { dot: "bg-rose-400", label: "Failed", text: "text-rose-300" },
};

interface DocumentCardProps {
  doc: DocumentItem;
  onRequestDelete: (doc: DocumentItem) => void;
  compact?: boolean;
}

export default function DocumentCard({ doc, onRequestDelete, compact = false }: DocumentCardProps) {
  const status = STATUS_STYLES[doc.status];

  return (
    <motion.div
      variants={fadeInUp}
      layout
      whileHover={{ y: -2 }}
      className={cn(
        "group relative rounded-xl border border-line bg-card p-3 transition hover:border-brand-400/40 hover:bg-card2",
        !compact && "sm:p-4"
      )}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500/15 text-accent">
          <FileText size={18} aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-content" title={doc.filename}>
            {doc.filename}
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-muted">
            <span className="rounded bg-card2 px-1.5 py-0.5 font-medium text-muted">
              {fileTypeLabel(doc.file_type)}
            </span>
            <span>{formatBytes(doc.file_size)}</span>
            <span aria-hidden>·</span>
            <span>{formatDate(doc.created_at)}</span>
          </div>
          <div className="mt-2 flex items-center gap-1.5">
            <span className={cn("h-1.5 w-1.5 rounded-full", status.dot)} aria-hidden />
            <span className={cn("text-[11px] font-medium", status.text)}>
              {status.label}
              {doc.status === "completed" && doc.total_chunks > 0 && (
                <span className="text-subtle"> · {doc.total_chunks} chunks</span>
              )}
              {doc.status === "completed" && doc.page_count ? (
                <span className="text-subtle"> · {doc.page_count}p</span>
              ) : null}
            </span>
          </div>
          {doc.status === "failed" && doc.error_message && (
            <p className="mt-1 text-[11px] text-rose-300/80">{doc.error_message}</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="mt-2 flex items-center justify-end gap-1">
        <a
          href={documentFileUrl(doc.id)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted transition hover:bg-card2 hover:text-content focus-visible:bg-card2"
          aria-label={`View ${doc.filename}`}
        >
          <ExternalLink size={13} aria-hidden /> View
        </a>
        <button
          onClick={() => onRequestDelete(doc)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted transition hover:bg-rose-500/15 hover:text-rose-300 focus-visible:bg-rose-500/15"
          aria-label={`Delete ${doc.filename}`}
        >
          <Trash2 size={13} aria-hidden /> Delete
        </button>
      </div>
    </motion.div>
  );
}
