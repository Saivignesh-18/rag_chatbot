import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { fadeInUp } from "@/lib/motion";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className="flex flex-col items-center justify-center px-6 py-12 text-center"
    >
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10 text-accent ring-1 ring-brand-500/20">
        <Icon size={30} aria-hidden />
      </div>
      <h3 className="text-lg font-semibold text-content">{title}</h3>
      {description && <p className="mt-2 max-w-xs text-sm text-muted">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </motion.div>
  );
}
