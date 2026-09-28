import { AnimatePresence, motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

// Friendly, generic loading messages shown while the request is in flight.
// These are client-side status hints (the backend answers in a single call and
// does not stream sub-progress), advancing on a timer.
const STAGES = [
  "Searching your documents...",
  "Reviewing relevant sections...",
  "Generating answer...",
];

export default function TypingIndicator() {
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const timers = [
      window.setTimeout(() => setStage(1), 1100),
      window.setTimeout(() => setStage(2), 2600),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-500/15 text-accent">
        <Sparkles size={16} aria-hidden />
      </div>
      <div className="flex items-center gap-3 rounded-2xl rounded-tl-sm border border-line bg-card px-4 py-3">
        <span className="flex gap-1" aria-hidden>
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="h-2 w-2 rounded-full bg-brand-300"
              animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
              transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
            />
          ))}
        </span>
        <AnimatePresence mode="wait">
          <motion.span
            key={stage}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
            className="text-sm text-muted"
            aria-live="polite"
          >
            {STAGES[stage]}
          </motion.span>
        </AnimatePresence>
      </div>
    </div>
  );
}
