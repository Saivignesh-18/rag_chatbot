import { motion } from "framer-motion";
import { FileText } from "lucide-react";
import { documentFileUrl } from "@/services/api";
import { fadeInUp } from "@/lib/motion";
import type { Source } from "@/types";

/** Build a link to the stored document, jumping to the page for PDFs. */
function sourceHref(source: Source): string {
  const base = documentFileUrl(source.document_id);
  return source.page_number ? `${base}#page=${source.page_number}` : base;
}

export default function SourceCitation({ source, index }: { source: Source; index?: number }) {
  const relevance = Math.round(source.similarity_score * 100);
  return (
    <motion.a
      variants={fadeInUp}
      href={sourceHref(source)}
      target="_blank"
      rel="noreferrer"
      whileHover={{ y: -2 }}
      className="block rounded-xl border border-line bg-card p-3 transition hover:border-brand-400/50 hover:bg-card2 focus-visible:border-brand-400"
      aria-label={`Open ${source.document_name}${source.page_number ? `, page ${source.page_number}` : ""} (relevance ${relevance}%)`}
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-500/15 text-accent">
          <FileText size={15} aria-hidden />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {index != null && (
              <span className="text-[11px] font-semibold text-accent">[{index}]</span>
            )}
            <p className="truncate text-sm font-medium text-content" title={source.document_name}>
              {source.document_name}
            </p>
          </div>
          <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted">
            {source.page_number != null ? <span>Page {source.page_number}</span> : <span>Document</span>}
            <span aria-hidden>·</span>
            <span>Relevance {relevance}%</span>
          </div>
          {/* Relevance bar */}
          <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-card2">
            <div
              className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-300"
              style={{ width: `${relevance}%` }}
            />
          </div>
        </div>
      </div>
    </motion.a>
  );
}
