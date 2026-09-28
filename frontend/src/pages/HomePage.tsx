import { motion } from "framer-motion";
import {
  ArrowUp,
  CalendarClock,
  CheckCircle2,
  FileText,
  FolderOpen,
  ListChecks,
  Loader2,
  MessagesSquare,
  Plus,
  Sparkles,
  Upload,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import CountUp from "@/components/common/CountUp";
import { useApp } from "@/context/AppContext";
import { useAuth } from "@/context/AuthContext";
import { useSessions } from "@/hooks/useSessions";
import { fadeInUp, listStagger } from "@/lib/motion";
import { createSession, toApiError } from "@/services/api";
import { fileTypeLabel, formatDate } from "@/lib/utils";

const STAT_CARDS = [
  { key: "documents", label: "Documents", icon: FileText, accent: "text-accent bg-brand-500/15" },
  { key: "ready_documents", label: "Ready", icon: CheckCircle2, accent: "text-emerald-300 bg-emerald-500/15" },
  { key: "chat_sessions", label: "Chat Sessions", icon: MessagesSquare, accent: "text-cyan-300 bg-cyan-500/15" },
  { key: "questions", label: "Questions Asked", icon: FolderOpen, accent: "text-fuchsia-300 bg-fuchsia-500/15" },
] as const;

const EXAMPLES = [
  { label: "Summarize the key points of my document", icon: FileText },
  { label: "What are the main requirements mentioned?", icon: ListChecks },
  { label: "Explain this topic in simple terms", icon: Sparkles },
  { label: "Find important dates and deadlines", icon: CalendarClock },
] as const;

function timeOfDay(): string {
  const h = new Date().getHours();
  if (h < 12) return "Morning";
  if (h < 18) return "Afternoon";
  return "Evening";
}

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { documents, stats, addToast, refreshDocuments, refreshStats } = useApp();
  const { sessions } = useSessions();

  const [prompt, setPrompt] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    void refreshDocuments();
    void refreshStats();
  }, [refreshDocuments, refreshStats]);

  const recentDocs = documents.slice(0, 5);
  const recentChats = sessions.slice(0, 5);
  const firstName = (user?.name ?? "there").split(" ")[0];

  const quickStart = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || starting) return;
      const readyIds = documents.filter((d) => d.status === "completed").map((d) => d.id);
      if (readyIds.length === 0) {
        addToast("info", "Upload a document first, then you can chat with it.");
        navigate("/app/documents");
        return;
      }
      setStarting(true);
      try {
        const session = await createSession(readyIds, q.slice(0, 60));
        navigate(`/app/chat/${session.id}`, { state: { initialQuestion: q } });
      } catch (err) {
        addToast("error", toApiError(err).message);
        setStarting(false);
      }
    },
    [documents, starting, addToast, navigate]
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:py-12">
        {/* Hero */}
        <motion.div
          variants={fadeInUp}
          initial="hidden"
          animate="show"
          className="flex flex-col items-center text-center"
        >
          {/* Orb */}
          <motion.div
            className="relative mb-6 h-20 w-20"
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            aria-hidden
          >
            <div className="absolute inset-0 rounded-full bg-gradient-to-br from-brand-400 via-fuchsia-500 to-brand-600 opacity-70 blur-xl" />
            <div className="absolute inset-1 rounded-full bg-gradient-to-br from-brand-300 via-fuchsia-400 to-brand-600" />
            <div className="absolute right-4 top-3 h-3.5 w-3.5 rounded-full bg-white/80 blur-[1px]" />
          </motion.div>

          <h1 className="text-3xl font-bold tracking-tight text-content sm:text-4xl">
            Good {timeOfDay()}, {firstName}
          </h1>
          <h2 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">
            <span className="text-content">What's on your </span>
            <span className="bg-gradient-to-r from-brand-500 to-fuchsia-500 bg-clip-text text-transparent">
              mind?
            </span>
          </h2>

          {/* Prompt input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void quickStart(prompt);
            }}
            className="mt-8 w-full max-w-2xl rounded-2xl border border-line bg-card p-3 text-left shadow-card transition focus-within:border-brand-400/50 focus-within:shadow-glow"
          >
            <div className="flex items-start gap-2">
              <Sparkles size={18} className="mt-2 shrink-0 text-accent" aria-hidden />
              <textarea
                rows={2}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void quickStart(prompt);
                  }
                }}
                placeholder="Ask your documents a question or make a request..."
                className="min-h-[2.5rem] w-full resize-none bg-transparent py-1.5 text-sm text-content placeholder:text-subtle focus:outline-none"
              />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={() => navigate("/app/documents")}
                className="inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-muted transition hover:bg-card2 hover:text-content"
              >
                <Upload size={14} aria-hidden /> Attach
              </button>
              <button
                type="submit"
                disabled={starting || !prompt.trim()}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Send"
              >
                {starting ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <ArrowUp size={16} aria-hidden />}
              </button>
            </div>
          </form>
        </motion.div>

        {/* Examples */}
        <div className="mt-10">
          <p className="mb-3 text-center text-xs font-semibold uppercase tracking-wider text-subtle">
            Get started with an example below
          </p>
          <motion.div
            variants={listStagger}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
          >
            {EXAMPLES.map((ex) => (
              <motion.button
                key={ex.label}
                variants={fadeInUp}
                onClick={() => void quickStart(ex.label)}
                disabled={starting}
                className="group flex h-32 flex-col justify-between rounded-2xl border border-line bg-card p-4 text-left transition hover:border-brand-400/40 hover:bg-card2 disabled:opacity-60"
              >
                <p className="text-sm font-medium text-content">{ex.label}</p>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-card2 text-muted transition group-hover:bg-brand-500/15 group-hover:text-accent">
                  <ex.icon size={16} aria-hidden />
                </span>
              </motion.button>
            ))}
          </motion.div>
        </div>

        {/* Workspace overview */}
        <div className="mt-12">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Your workspace</h2>
          <motion.div
            variants={listStagger}
            initial="hidden"
            animate="show"
            className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4"
          >
            {STAT_CARDS.map((card) => (
              <motion.div
                key={card.key}
                variants={fadeInUp}
                className="rounded-2xl border border-line bg-card p-4 shadow-card sm:p-5"
              >
                <span className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl ${card.accent}`}>
                  <card.icon size={20} aria-hidden />
                </span>
                <div className="text-2xl font-bold text-content">
                  <CountUp value={stats[card.key]} />
                </div>
                <div className="text-sm text-muted">{card.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* Quick actions */}
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            onClick={() => navigate("/app/documents")}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-500"
          >
            <Upload size={16} aria-hidden /> Upload Document
          </button>
          <button
            onClick={() => navigate("/app/documents")}
            className="inline-flex items-center gap-2 rounded-xl border border-line bg-card px-4 py-2.5 text-sm font-semibold text-content transition hover:bg-card2"
          >
            <Plus size={16} aria-hidden /> Start New Chat
          </button>
        </div>

        {/* Recent */}
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">Recent Documents</h2>
              <button onClick={() => navigate("/app/documents")} className="text-xs text-accent hover:text-brand-200">
                View all
              </button>
            </div>
            {recentDocs.length === 0 ? (
              <p className="rounded-xl border border-dashed border-line px-4 py-6 text-center text-sm text-subtle">
                No documents yet.
              </p>
            ) : (
              <div className="space-y-2">
                {recentDocs.map((d) => (
                  <div key={d.id} className="flex items-center gap-3 rounded-xl border border-line bg-card p-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500/15 text-accent">
                      <FileText size={16} aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-content">{d.filename}</p>
                      <p className="text-[11px] text-subtle">
                        {fileTypeLabel(d.file_type)} · {formatDate(d.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Recent Chats</h2>
            {recentChats.length === 0 ? (
              <p className="rounded-xl border border-dashed border-line px-4 py-6 text-center text-sm text-subtle">
                No chats yet.
              </p>
            ) : (
              <div className="space-y-2">
                {recentChats.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => navigate(`/app/chat/${s.id}`)}
                    className="flex w-full items-center gap-3 rounded-xl border border-line bg-card p-3 text-left transition hover:bg-card2"
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/15 text-cyan-300">
                      <MessagesSquare size={16} aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm text-content">{s.title ?? "Untitled chat"}</p>
                      <p className="text-[11px] text-subtle">
                        {s.document_count} doc{s.document_count === 1 ? "" : "s"} · {formatDate(s.updated_at)}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
