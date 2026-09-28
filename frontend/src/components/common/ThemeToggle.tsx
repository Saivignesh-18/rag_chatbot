import { AnimatePresence, motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";

export default function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const label = isDark ? "Switch to light theme" : "Switch to dark theme";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={cn(
        "relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-lg border border-line bg-card text-muted transition hover:bg-card2 hover:text-content",
        className
      )}
      aria-label={label}
      title={label}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={isDark ? "moon" : "sun"}
          initial={{ opacity: 0, rotate: -90, scale: 0.5 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 90, scale: 0.5 }}
          transition={{ duration: 0.18 }}
          className="absolute inline-flex"
        >
          {isDark ? <Moon size={18} aria-hidden /> : <Sun size={18} aria-hidden />}
        </motion.span>
      </AnimatePresence>
    </button>
  );
}
