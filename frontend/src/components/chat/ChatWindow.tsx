import { AnimatePresence, motion } from "framer-motion";
import { MessagesSquare, Sparkles } from "lucide-react";
import { useEffect, useRef } from "react";
import EmptyState from "@/components/common/EmptyState";
import type { ChatMessage as ChatMessageT } from "@/types";
import ChatInput from "./ChatInput";
import ChatMessage from "./ChatMessage";
import TypingIndicator from "./TypingIndicator";

interface ChatWindowProps {
  messages: ChatMessageT[];
  sending: boolean;
  hasDocuments: boolean;
  onSend: (text: string) => void;
}

const STARTERS = [
  "Summarize the key points of my documents.",
  "What are the main requirements?",
  "List the important policies.",
];

export default function ChatWindow({ messages, sending, hasDocuments, onSend }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 sm:px-6" role="log" aria-live="polite">
        {isEmpty ? (
          <div className="flex h-full items-center justify-center">
            {hasDocuments ? (
              <div className="w-full max-w-lg text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-500/15 text-accent">
                  <Sparkles size={28} aria-hidden />
                </div>
                <h2 className="text-xl font-semibold text-content">Ask your documents anything</h2>
                <p className="mt-2 text-sm text-muted">
                  Answers are grounded only in the files you've selected, with verifiable sources.
                </p>
                <div className="mt-6 grid gap-2">
                  {STARTERS.map((s) => (
                    <button
                      key={s}
                      onClick={() => onSend(s)}
                      className="rounded-xl border border-line bg-card px-4 py-2.5 text-left text-sm text-muted transition hover:border-brand-400/40 hover:bg-card2 hover:text-content"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState
                icon={MessagesSquare}
                title="Your document workspace is empty"
                description="Upload a PDF, DOCX, or TXT file from the panel on the left to start asking questions."
              />
            )}
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            <AnimatePresence initial={false}>
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
            </AnimatePresence>
            {sending && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <TypingIndicator />
              </motion.div>
            )}
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-line bg-bg/60 px-4 py-3 sm:px-6">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSend={onSend}
            disabled={sending || !hasDocuments}
            placeholder={
              hasDocuments
                ? "Ask something about your documents..."
                : "Upload a document to start chatting..."
            }
          />
        </div>
      </div>
    </div>
  );
}
