import { AnimatePresence, motion } from "framer-motion";
import { FileText, Home, LogOut, MessagesSquare, User as UserIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

function Avatar({ src, name, size = 32 }: { src: string | null; name: string | null; size?: number }) {
  const initial = (name ?? "?").trim().charAt(0).toUpperCase() || "?";
  if (src) {
    return (
      <img
        src={src}
        alt={name ?? "Profile"}
        referrerPolicy="no-referrer"
        className="rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <span
      className="flex items-center justify-center rounded-full bg-brand-600 font-semibold text-white"
      style={{ width: size, height: size, fontSize: size * 0.42 }}
    >
      {initial}
    </span>
  );
}

export default function ProfileMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const go = (path: string) => {
    setOpen(false);
    navigate(path);
  };

  const items = [
    { label: "Home", icon: Home, path: "/app/home" },
    { label: "Documents", icon: FileText, path: "/app/documents" },
    { label: "Chat", icon: MessagesSquare, path: "/app/chat" },
  ];

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-line bg-card py-1 pl-1 pr-2.5 transition hover:bg-card2"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Open profile menu"
      >
        <Avatar src={user?.profile_picture ?? null} name={user?.name ?? null} />
        <span className="hidden max-w-[120px] truncate text-sm font-medium text-content sm:block">
          {user?.name ?? "Account"}
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            role="menu"
            className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-2xl border border-line bg-panel shadow-glow"
          >
            <div className="flex items-center gap-3 border-b border-line p-4">
              <Avatar src={user?.profile_picture ?? null} name={user?.name ?? null} size={40} />
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-content">{user?.name ?? "User"}</p>
                <p className="truncate text-xs text-muted">{user?.email}</p>
                <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-card2 px-2 py-0.5 text-[10px] text-muted">
                  <UserIcon size={10} aria-hidden /> Google
                </span>
              </div>
            </div>
            <div className="p-1.5">
              {items.map((it) => (
                <button
                  key={it.path}
                  role="menuitem"
                  onClick={() => go(it.path)}
                  className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-content transition hover:bg-card2"
                >
                  <it.icon size={16} className="text-muted" aria-hidden /> {it.label}
                </button>
              ))}
              <button
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  void logout();
                }}
                className="mt-1 flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-rose-300 transition hover:bg-rose-500/10"
              >
                <LogOut size={16} aria-hidden /> Logout
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
