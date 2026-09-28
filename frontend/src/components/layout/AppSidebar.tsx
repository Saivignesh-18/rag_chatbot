import { FileText, Home, LogOut, MessagesSquare, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import { useAuth } from "@/context/AuthContext";
import { useSessions } from "@/hooks/useSessions";
import { cn, formatDate } from "@/lib/utils";
import type { ChatSession } from "@/types";

const NAV = [
  { to: "/app/home", label: "Home", icon: Home, end: false },
  { to: "/app/documents", label: "Documents", icon: FileText, end: false },
];

export default function AppSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const { sessions, remove } = useSessions();
  const [pendingDelete, setPendingDelete] = useState<ChatSession | null>(null);

  const handleNav = () => onNavigate?.();

  const confirmDelete = async () => {
    const target = pendingDelete;
    setPendingDelete(null);
    if (!target) return;
    await remove(target.id);
    // If we just deleted the chat we're currently viewing, move off it.
    if (location.pathname === `/app/chat/${target.id}`) {
      handleNav();
      navigate("/app/home");
    }
  };

  return (
    <div className="flex h-full flex-col bg-bg/70">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 text-white shadow-glow">
          <FileText size={16} aria-hidden />
        </span>
        <span className="text-sm font-semibold text-content">Document AI</span>
      </div>

      <div className="px-3">
        <button
          onClick={() => {
            handleNav();
            navigate("/app/documents");
          }}
          className="mb-3 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-brand-500"
        >
          <Plus size={16} aria-hidden /> New chat
        </button>
      </div>

      {/* Nav */}
      <nav className="space-y-1 px-3" aria-label="Primary">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={handleNav}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition",
                isActive ? "bg-card2 text-content" : "text-muted hover:bg-card hover:text-content"
              )
            }
          >
            <item.icon size={16} aria-hidden /> {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Recent chats */}
      <div className="mt-5 flex min-h-0 flex-1 flex-col px-3">
        <p className="mb-2 flex items-center gap-2 px-1 text-xs font-semibold uppercase tracking-wide text-subtle">
          <MessagesSquare size={13} aria-hidden /> Recent chats
        </p>
        <div className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <p className="px-2 py-3 text-xs text-subtle">No chats yet. Select documents to start one.</p>
          ) : (
            sessions.map((s) => (
              <div key={s.id} className="group relative">
                <NavLink
                  to={`/app/chat/${s.id}`}
                  onClick={handleNav}
                  className={({ isActive }) =>
                    cn(
                      "block rounded-lg py-2 pl-2.5 pr-9 text-sm transition",
                      isActive ? "bg-brand-500/15 text-content" : "text-muted hover:bg-card"
                    )
                  }
                >
                  <span className="block truncate">{s.title ?? "Untitled chat"}</span>
                  <span className="block text-[11px] text-subtle">
                    {s.document_count} doc{s.document_count === 1 ? "" : "s"} · {formatDate(s.updated_at)}
                  </span>
                </NavLink>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setPendingDelete(s);
                  }}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-subtle opacity-100 transition hover:bg-rose-500/10 hover:text-rose-300 focus:opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100"
                  aria-label={`Delete chat: ${s.title ?? "Untitled chat"}`}
                  title="Delete chat"
                >
                  <Trash2 size={14} aria-hidden />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Logout */}
      <div className="border-t border-line p-3">
        <button
          onClick={() => void logout()}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-muted transition hover:bg-rose-500/10 hover:text-rose-300"
        >
          <LogOut size={16} aria-hidden /> Logout
        </button>
      </div>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete chat?"
        description={
          pendingDelete
            ? `"${pendingDelete.title ?? "Untitled chat"}" and its messages will be permanently deleted.`
            : undefined
        }
        confirmLabel="Delete"
        destructive
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
