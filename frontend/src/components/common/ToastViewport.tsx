import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { useApp, type ToastType } from "@/context/AppContext";
import { cn } from "@/lib/utils";

const ICONS: Record<ToastType, typeof Info> = {
  success: CheckCircle2,
  error: XCircle,
  info: Info,
};

const STYLES: Record<ToastType, string> = {
  success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-200",
  error: "border-rose-500/30 bg-rose-500/10 text-rose-200",
  info: "border-brand-500/30 bg-brand-500/10 text-brand-200",
};

export default function ToastViewport() {
  const { toasts, dismissToast } = useApp();

  return (
    <div
      className="pointer-events-none fixed inset-x-0 bottom-4 z-[100] flex flex-col items-center gap-2 px-4 sm:items-end sm:pr-6"
      aria-live="polite"
      aria-atomic="true"
    >
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = ICONS[toast.type];
          return (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              className={cn(
                "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 shadow-card backdrop-blur",
                STYLES[toast.type]
              )}
              role="status"
            >
              <Icon size={18} className="mt-0.5 shrink-0" aria-hidden />
              <p className="flex-1 text-sm leading-snug text-content">{toast.message}</p>
              <button
                onClick={() => dismissToast(toast.id)}
                className="rounded-md p-0.5 text-muted transition hover:text-content"
                aria-label="Dismiss notification"
              >
                <X size={16} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
