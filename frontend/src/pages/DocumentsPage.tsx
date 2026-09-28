import { AnimatePresence, motion } from "framer-motion";
import { FolderOpen, Loader2, MessagesSquare, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import EmptyState from "@/components/common/EmptyState";
import DocumentUpload from "@/components/documents/DocumentUpload";
import SelectableDocumentCard from "@/components/documents/SelectableDocumentCard";
import { useApp } from "@/context/AppContext";
import { listStagger } from "@/lib/motion";
import { createSession, toApiError } from "@/services/api";
import type { DocumentItem } from "@/types";

type FilterKey = "all" | "pdf" | "docx" | "txt" | "processing" | "ready" | "failed";
type SortKey = "newest" | "oldest" | "az" | "za";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pdf", label: "PDF" },
  { key: "docx", label: "DOCX" },
  { key: "txt", label: "TXT" },
  { key: "ready", label: "Ready" },
  { key: "processing", label: "Processing" },
  { key: "failed", label: "Failed" },
];

export default function DocumentsPage() {
  const navigate = useNavigate();
  const { documents, documentsLoading, refreshDocuments, removeDocument, addToast } = useApp();

  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
  const [sort, setSort] = useState<SortKey>("newest");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  const visible = useMemo(() => {
    let list = documents;
    const q = query.trim().toLowerCase();
    if (q) list = list.filter((d) => d.filename.toLowerCase().includes(q));
    if (filter !== "all") {
      list = list.filter((d) => {
        if (filter === "ready") return d.status === "completed";
        if (filter === "processing") return d.status === "processing" || d.status === "pending";
        if (filter === "failed") return d.status === "failed";
        return d.file_type === filter;
      });
    }
    const sorted = [...list];
    sorted.sort((a, b) => {
      switch (sort) {
        case "oldest":
          return a.created_at.localeCompare(b.created_at);
        case "az":
          return a.filename.localeCompare(b.filename);
        case "za":
          return b.filename.localeCompare(a.filename);
        default:
          return b.created_at.localeCompare(a.created_at);
      }
    });
    return sorted;
  }, [documents, query, filter, sort]);

  const readyCount = documents.filter((d) => d.status === "completed").length;

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const selectAllVisible = () => {
    const ready = visible.filter((d) => d.status === "completed").map((d) => d.id);
    setSelected(new Set(ready));
  };
  const clearSelection = () => setSelected(new Set());

  const startChat = async () => {
    if (selected.size === 0) return;
    setStarting(true);
    try {
      const session = await createSession(Array.from(selected));
      navigate(`/app/chat/${session.id}`);
    } catch (err) {
      addToast("error", toApiError(err).message);
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:py-8">
          <div className="mb-5">
            <h1 className="text-xl font-bold text-content sm:text-2xl">Documents</h1>
            <p className="mt-1 text-sm text-muted">
              Upload documents, then select the ones you want to chat with.
            </p>
          </div>

          <div className="mb-6">
            <DocumentUpload variant="compact" />
          </div>

          {/* Toolbar */}
          <div className="mb-4 flex flex-col gap-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="relative w-full sm:max-w-xs">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-subtle" aria-hidden />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search documents..."
                  className="w-full rounded-lg border border-line bg-card py-2 pl-9 pr-3 text-sm text-content placeholder:text-subtle focus:border-brand-400/60 focus:outline-none"
                  aria-label="Search documents"
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-subtle">{documents.length} documents</span>
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortKey)}
                  className="rounded-lg border border-line bg-panel px-2.5 py-2 text-sm text-content focus:border-brand-400/60 focus:outline-none"
                  aria-label="Sort documents"
                >
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="az">Name A-Z</option>
                  <option value="za">Name Z-A</option>
                </select>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={
                    "rounded-full px-3 py-1 text-xs font-medium transition " +
                    (filter === f.key
                      ? "bg-brand-600 text-white"
                      : "border border-line bg-card text-muted hover:bg-card2")
                  }
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* List */}
          {documentsLoading ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-28 animate-pulse rounded-xl bg-card" />
              ))}
            </div>
          ) : documents.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-line bg-card">
              <EmptyState
                icon={FolderOpen}
                title="Your document workspace is empty"
                description="Upload a PDF, DOCX, or TXT file above to get started."
              />
            </div>
          ) : visible.length === 0 ? (
            <p className="py-10 text-center text-sm text-subtle">No documents match your search or filters.</p>
          ) : (
            <motion.div
              variants={listStagger}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 gap-3 pb-24 sm:grid-cols-2 xl:grid-cols-3"
            >
              <AnimatePresence mode="popLayout">
                {visible.map((doc) => (
                  <SelectableDocumentCard
                    key={doc.id}
                    doc={doc}
                    selected={selected.has(doc.id)}
                    onToggle={toggle}
                    onRequestDelete={setDeleteTarget}
                  />
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      </div>

      {/* Sticky selection action bar */}
      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0 }}
            className="shrink-0 border-t border-line bg-bg/90 px-4 py-3 backdrop-blur sm:px-6"
          >
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="text-sm font-semibold text-content">
                  Selected: {selected.size} document{selected.size === 1 ? "" : "s"}
                </span>
                <button
                  onClick={selectAllVisible}
                  className="text-xs text-accent hover:text-brand-200"
                >
                  Select all ready ({readyCount})
                </button>
                <button
                  onClick={clearSelection}
                  className="inline-flex items-center gap-1 text-xs text-muted hover:text-content"
                >
                  <X size={13} aria-hidden /> Clear
                </button>
              </div>
              <button
                onClick={() => void startChat()}
                disabled={starting}
                className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-500 disabled:opacity-60"
              >
                {starting ? <Loader2 size={16} className="animate-spin" aria-hidden /> : <MessagesSquare size={16} aria-hidden />}
                Start Chat With Selected
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <ConfirmDialog
        open={deleteTarget !== null}
        destructive
        title="Delete document?"
        description={
          deleteTarget
            ? `"${deleteTarget.filename}" and its indexed chunks will be permanently removed.`
            : ""
        }
        confirmLabel="Delete"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) {
            void removeDocument(deleteTarget.id);
            setSelected((prev) => {
              const next = new Set(prev);
              next.delete(deleteTarget.id);
              return next;
            });
          }
          setDeleteTarget(null);
        }}
      />
    </div>
  );
}
