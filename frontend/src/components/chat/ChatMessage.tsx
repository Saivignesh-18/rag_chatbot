import { motion } from "framer-motion";
import { AlertCircle, FileText, Sparkles, User } from "lucide-react";
import { documentFileUrl } from "@/services/api";
import { isRefusal } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageT, Source } from "@/types";
import MarkdownContent from "./MarkdownContent";

const SUGGESTIONS = [
  "topics covered in your documents",
  "specific requirements",
  "policies",
  "procedures",
  "data mentioned in the documents",
];

function SourcePills({ sources }: { sources: Source[] }) {
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {sources.map((s) => (
        <a
          key={s.chunk_id}
          href={documentFileUrl(s.document_id) + (s.page_number ? `#page=${s.page_number}` : "")}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 rounded-full border border-line bg-card px-2.5 py-1 text-[11px] text-muted transition hover:border-brand-400/50 hover:text-content"
          title={`${s.document_name}${s.page_number ? `, page ${s.page_number}` : ""} · ${Math.round(
            s.similarity_score * 100
          )}% relevance`}
        >
          <FileText size={11} aria-hidden />
          <span className="max-w-[140px] truncate">{s.document_name}</span>
          {s.page_number != null && <span className="text-subtle">p{s.page_number}</span>}
        </a>
      ))}
    </div>
  );
}

function NoAnswer() {
  return (
    <div className="rounded-2xl rounded-tl-sm border border-amber-500/20 bg-amber-500/5 px-4 py-3">
      <p className="text-sm text-content">
        I couldn't find this information in the provided documents.
      </p>
      <p className="mt-3 text-xs font-medium text-muted">Try asking about:</p>
      <ul className="mt-1.5 space-y-1">
        {SUGGESTIONS.map((s) => (
          <li key={s} className="flex items-center gap-2 text-xs text-muted">
            <span className="h-1 w-1 rounded-full bg-amber-400" aria-hidden />
            {s}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ChatMessage({ message }: { message: ChatMessageT }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22 }}
        className="flex items-start justify-end gap-3"
      >
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-card sm:max-w-[75%]">
          {message.content}
        </div>
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-card2 text-muted">
          <User size={16} aria-hidden />
        </span>
      </motion.div>
    );
  }

  const refused = isRefusal(message.content);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24 }}
      className="flex items-start gap-3"
    >
      <span
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          message.error ? "bg-rose-500/15 text-rose-300" : "bg-brand-500/15 text-accent"
        )}
      >
        {message.error ? <AlertCircle size={16} aria-hidden /> : <Sparkles size={16} aria-hidden />}
      </span>

      <div className="min-w-0 max-w-[85%] sm:max-w-[78%]">
        {refused ? (
          <NoAnswer />
        ) : (
          <div
            className={cn(
              "rounded-2xl rounded-tl-sm border px-4 py-3",
              message.error
                ? "border-rose-500/20 bg-rose-500/5 text-rose-100"
                : "border-line bg-card"
            )}
          >
            <MarkdownContent content={message.content} />
          </div>
        )}

        {!refused && message.sources && message.sources.length > 0 && (
          <SourcePills sources={message.sources} />
        )}
      </div>
    </motion.div>
  );
}
