import { motion } from "framer-motion";
import { Check, ExternalLink, FileText, Trash2 } from "lucide-react";
import { documentFileUrl } from "@/services/api";
import { cn, fileTypeLabel, formatBytes, formatDate } from "@/lib/utils";
import { fadeInUp } from "@/lib/motion";
import type { DocumentItem, DocumentStatus } from "@/types";

const STATUS: Record<DocumentStatus, { dot: string; label: string; text: string }> = {
  completed: { dot: "bg-emerald-400", label: "Ready", text: "text-emerald-300" },
  processing: { dot: "bg-amber-400 animate-pulse", label: "Processing", text: "text-amber-300" },
  pending: { dot: "bg-slate-400", label: "Pending", text: "text-muted" },
  failed: { dot: "bg-rose-400", label: "Failed", text: "text-rose-300" },
};

interface Props {
  doc: DocumentItem;
  selected: boolean;
  onToggle: (id: string) => void;
  onRequestDelete: (doc: DocumentItem) => void;
}

export default function SelectableDocumentCard({ doc, selected, onToggle, onRequestDelete }: Props) {
  const status = STATUS[doc.status];
  const selectable = doc.status === "completed";

  return (
    <motion.div
      variants={fadeInUp}
      layout
      className={cn(
        "group relative rounded-xl border p-3 transition sm:p-4",
        selected
          ? "border-brand-400/70 bg-brand-500/10 shadow-glow"
          : "border-line bg-card hover:border-line hover:bg-card2"
      )}
    >
      <div className="flex items-start gap-3">
        {/* Checkbox */}
        <button
          onClick={() => selectable && onToggle(doc.id)}
          disabled={!selectable}
          role="checkbox"
          aria-checked={selected}
          aria-label={selectable ? `Select ${doc.filename}` : `${doc.filename} is not ready`}
          className={cn(
            "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition",
            selected
              ? "border-brand-400 bg-brand-500 text-white"
              : selectable
                ? "border-line hover:border-brand-400"
                : "cursor-not-allowed border-line opacity-40"
          )}
        >
          {selected && <Check size={13} aria-hidden />}
        </button>

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
            <span className="inline-flex items-center gap-1">
              <span className={cn("h-1.5 w-1.5 rounded-full", status.dot)} aria-hidden />
              <span className={status.text}>{status.label}</span>
            </span>
          </div>
          <p className="mt-1 text-[11px] text-subtle">Uploaded {formatDate(doc.created_at)}</p>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-end gap-1">
        <a
          href={documentFileUrl(doc.id)}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted transition hover:bg-card2 hover:text-content"
          aria-label={`View ${doc.filename}`}
        >
          <ExternalLink size={13} aria-hidden /> View
        </a>
        <button
          onClick={() => onRequestDelete(doc)}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted transition hover:bg-rose-500/15 hover:text-rose-300"
          aria-label={`Delete ${doc.filename}`}
        >
          <Trash2 size={13} aria-hidden /> Delete
        </button>
      </div>
    </motion.div>
  );
}
