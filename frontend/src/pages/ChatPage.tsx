import { AlertCircle, Check, FileText, Loader2, Quote, Settings2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ChatWindow from "@/components/chat/ChatWindow";
import Drawer from "@/components/common/Drawer";
import SourcePanel from "@/components/sources/SourcePanel";
import { useApp } from "@/context/AppContext";
import {
  getSession,
  sendChat,
  toApiError,
  updateSessionScope,
} from "@/services/api";
import { cn } from "@/lib/utils";
import type { ChatMessage, ChatSessionDetail, Source } from "@/types";

let tmp = 0;
const localId = () => `local-${Date.now()}-${tmp++}`;

export default function ChatPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { documents, refreshDocuments, refreshStats, addToast } = useApp();

  // An initial question can be passed from the Home quick-start; auto-send once.
  const initialQuestion = (location.state as { initialQuestion?: string } | null)?.initialQuestion;
  const sentInitial = useRef(false);

  const [session, setSession] = useState<ChatSessionDetail | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const [scopeOpen, setScopeOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const loadSession = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const { session: s, messages: msgs } = await getSession(sessionId);
      setSession(s);
      setMessages(
        msgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources ?? undefined,
          created_at: m.created_at,
        }))
      );
    } catch (err) {
      setLoadError(toApiError(err).message);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  const handleSend = useCallback(
    async (text: string) => {
      if (sending || !session) return;
      setMessages((prev) => [...prev, { id: localId(), role: "user", content: text }]);
      setSending(true);
      try {
        const res = await sendChat(session.id, text);
        setMessages((prev) => [
          ...prev,
          { id: localId(), role: "assistant", content: res.answer, sources: res.sources },
        ]);
        void refreshStats();
      } catch (err) {
        const msg = toApiError(err).message;
        setMessages((prev) => [...prev, { id: localId(), role: "assistant", content: msg, error: true }]);
        addToast("error", msg);
      } finally {
        setSending(false);
      }
    },
    [sending, session, refreshStats, addToast]
  );

  // Auto-send a question handed off from the Home page quick-start, exactly once.
  useEffect(() => {
    if (sentInitial.current || loading || !session || !initialQuestion || messages.length > 0) return;
    sentInitial.current = true;
    void handleSend(initialQuestion);
    // Clear navigation state so a refresh or back-nav doesn't resend it.
    navigate(location.pathname, { replace: true, state: null });
  }, [loading, session, initialQuestion, messages.length, handleSend, navigate, location.pathname]);

  const latestSources: Source[] = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.sources && m.sources.length > 0) return m.sources;
    }
    return [];
  }, [messages]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 size={22} className="animate-spin text-accent" aria-hidden />
      </div>
    );
  }

  if (loadError || !session) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-6 text-center">
        <AlertCircle size={28} className="text-rose-300" aria-hidden />
        <p className="text-sm text-muted">{loadError ?? "Chat session not found."}</p>
        <button
          onClick={() => navigate("/app/documents")}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
        >
          Go to Documents
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Scope bar */}
      <div className="shrink-0 border-b border-line bg-bg/60 px-4 py-2.5 sm:px-6">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-medium text-muted">
              Chatting with {session.document_count} document{session.document_count === 1 ? "" : "s"}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              {session.documents.length === 0 ? (
                <span className="text-[11px] text-subtle">No documents selected — searching all your documents.</span>
              ) : (
                session.documents.map((d) => (
                  <span
                    key={d.id}
                    className="inline-flex max-w-[180px] items-center gap-1 rounded-full border border-line bg-card px-2 py-0.5 text-[11px] text-muted"
                    title={d.filename}
                  >
                    <FileText size={11} aria-hidden />
                    <span className="truncate">{d.filename}</span>
                  </span>
                ))
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={() => {
                void refreshDocuments();
                setScopeOpen(true);
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-card px-2.5 py-1.5 text-xs font-medium text-content transition hover:bg-card2"
            >
              <Settings2 size={14} aria-hidden /> Change Documents
            </button>
            <button
              onClick={() => setSourcesOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-card px-2.5 py-1.5 text-xs font-medium text-content transition hover:bg-card2 lg:hidden"
            >
              <Quote size={14} aria-hidden /> Sources
              {latestSources.length > 0 && (
                <span className="rounded-full bg-brand-500/20 px-1.5 text-[10px] text-brand-200">
                  {latestSources.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <ChatWindow messages={messages} sending={sending} hasDocuments onSend={handleSend} />
        </div>
        <aside className="hidden w-80 shrink-0 border-l border-line xl:block">
          <SourcePanel sources={latestSources} />
        </aside>
      </div>

      {/* Sources drawer (mobile/tablet) */}
      <Drawer open={sourcesOpen} onClose={() => setSourcesOpen(false)} side="right" ariaLabel="Sources">
        <SourcePanel sources={latestSources} onClose={() => setSourcesOpen(false)} />
      </Drawer>

      {/* Change documents drawer */}
      <ChangeDocumentsDrawer
        open={scopeOpen}
        onClose={() => setScopeOpen(false)}
        documents={documents}
        currentIds={session.documents.map((d) => d.id)}
        onSave={async (ids) => {
          try {
            const updated = await updateSessionScope(session.id, ids);
            setSession(updated);
            addToast("success", "Document scope updated.");
            setScopeOpen(false);
          } catch (err) {
            addToast("error", toApiError(err).message);
          }
        }}
      />
    </div>
  );
}

function ChangeDocumentsDrawer({
  open,
  onClose,
  documents,
  currentIds,
  onSave,
}: {
  open: boolean;
  onClose: () => void;
  documents: import("@/types").DocumentItem[];
  currentIds: string[];
  onSave: (ids: string[]) => Promise<void>;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set(currentIds));
  const [saving, setSaving] = useState(false);

  // Re-sync when opened.
  useEffect(() => {
    if (open) setSelected(new Set(currentIds));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const ready = documents.filter((d) => d.status === "completed");

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <Drawer open={open} onClose={onClose} side="right" widthClass="w-[90vw] max-w-md" ariaLabel="Change documents" allowDesktop>
      <div className="flex h-full flex-col">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold text-content">Change documents</h2>
          <p className="mt-0.5 text-[11px] text-subtle">Select which documents this chat should use.</p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {ready.length === 0 ? (
            <p className="px-2 py-6 text-center text-sm text-subtle">No ready documents to select.</p>
          ) : (
            <div className="space-y-2">
              {ready.map((d) => {
                const isSel = selected.has(d.id);
                return (
                  <button
                    key={d.id}
                    onClick={() => toggle(d.id)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-xl border p-3 text-left transition",
                      isSel ? "border-brand-400/70 bg-brand-500/10" : "border-line bg-card hover:bg-card2"
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-5 w-5 shrink-0 items-center justify-center rounded-md border",
                        isSel ? "border-brand-400 bg-brand-500 text-white" : "border-line"
                      )}
                    >
                      {isSel && <Check size={13} aria-hidden />}
                    </span>
                    <FileText size={16} className="shrink-0 text-accent" aria-hidden />
                    <span className="min-w-0 flex-1 truncate text-sm text-content">{d.filename}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-line p-3">
          <span className="text-xs text-muted">{selected.size} selected</span>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="rounded-lg border border-line px-3 py-2 text-sm text-content hover:bg-card"
            >
              Cancel
            </button>
            <button
              onClick={async () => {
                setSaving(true);
                await onSave(Array.from(selected));
                setSaving(false);
              }}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-60"
            >
              {saving && <Loader2 size={14} className="animate-spin" aria-hidden />}
              Save
            </button>
          </div>
        </div>
      </div>
    </Drawer>
  );
}
