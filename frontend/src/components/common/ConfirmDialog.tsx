import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { useEffect, useRef } from "react";
import { scaleIn } from "@/lib/motion";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Accessible confirmation modal with focus management and Escape-to-close. */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    confirmRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[90] flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-title"
        >
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} aria-hidden />
          <motion.div
            variants={scaleIn}
            initial="hidden"
            animate="show"
            exit="exit"
            className="relative w-full max-w-md rounded-2xl border border-line bg-panel p-6 shadow-glow"
          >
            <div className="flex items-start gap-4">
              <div
                className={
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl " +
                  (destructive ? "bg-rose-500/15 text-rose-300" : "bg-brand-500/15 text-accent")
                }
              >
                <AlertTriangle size={22} aria-hidden />
              </div>
              <div className="flex-1">
                <h2 id="confirm-title" className="text-lg font-semibold text-content">
                  {title}
                </h2>
                {description && <p className="mt-1 text-sm text-muted">{description}</p>}
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={onCancel}
                className="rounded-lg border border-line px-4 py-2 text-sm font-medium text-content transition hover:bg-card"
              >
                {cancelLabel}
              </button>
              <button
                ref={confirmRef}
                onClick={onConfirm}
                className={
                  "rounded-lg px-4 py-2 text-sm font-semibold text-white transition " +
                  (destructive
                    ? "bg-rose-600 hover:bg-rose-500"
                    : "bg-brand-600 hover:bg-brand-500")
                }
              >
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
