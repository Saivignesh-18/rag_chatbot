import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { useApp } from "@/context/AppContext";
import { listStagger } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { DocumentItem } from "@/types";
import ConfirmDialog from "@/components/common/ConfirmDialog";
import DocumentCard from "./DocumentCard";

interface DocumentListProps {
  grid?: boolean;
  compact?: boolean;
}

export default function DocumentList({ grid = false, compact = false }: DocumentListProps) {
  const { documents, removeDocument } = useApp();
  const [target, setTarget] = useState<DocumentItem | null>(null);

  return (
    <>
      <motion.div
        variants={listStagger}
        initial="hidden"
        animate="show"
        className={cn(grid ? "grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3" : "space-y-2")}
      >
        <AnimatePresence mode="popLayout">
          {documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onRequestDelete={setTarget} compact={compact} />
          ))}
        </AnimatePresence>
      </motion.div>

      <ConfirmDialog
        open={target !== null}
        destructive
        title="Delete document?"
        description={
          target
            ? `"${target.filename}" and its indexed chunks will be permanently removed. This cannot be undone.`
            : ""
        }
        confirmLabel="Delete"
        onCancel={() => setTarget(null)}
        onConfirm={() => {
          if (target) void removeDocument(target.id);
          setTarget(null);
        }}
      />
    </>
  );
}
