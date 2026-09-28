import { AnimatePresence, motion } from "framer-motion";
import { useEffect, type ReactNode } from "react";
import { drawerLeft, drawerRight } from "@/lib/motion";
import { cn } from "@/lib/utils";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  side?: "left" | "right";
  widthClass?: string;
  children: ReactNode;
  ariaLabel: string;
  /**
   * By default the drawer is mobile-only (hidden at the lg breakpoint and up),
   * since the nav/sources drawers have desktop equivalents. Set this to true for
   * drawers that must also work on desktop (e.g. "Change Documents").
   */
  allowDesktop?: boolean;
}

export default function Drawer({
  open,
  onClose,
  side = "left",
  widthClass = "w-[85vw] max-w-sm",
  children,
  ariaLabel,
  allowDesktop = false,
}: DrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className={cn("fixed inset-0 z-50", !allowDesktop && "lg:hidden")}>
          <motion.div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden
          />
          <motion.aside
            variants={side === "left" ? drawerLeft : drawerRight}
            initial="hidden"
            animate="show"
            exit="exit"
            className={cn(
              "absolute inset-y-0 border-line bg-bg shadow-glow",
              side === "left" ? "left-0 border-r" : "right-0 border-l",
              widthClass
            )}
            role="dialog"
            aria-modal="true"
            aria-label={ariaLabel}
          >
            {children}
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
}
