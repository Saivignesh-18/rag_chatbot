import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, FileText, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type UploadStatus = "uploading" | "processing" | "done" | "error";

export interface UploadJob {
  id: string;
  name: string;
  status: UploadStatus;
  percent: number;
  chunks?: number;
  error?: string;
}

/**
 * Honest staged progress:
 * - "uploading" shows the real upload percentage from the browser.
 * - "processing" is indeterminate (the backend performs extract -> embed -> index
 *   in one synchronous call and does not stream sub-progress, so we do not fake it).
 * - "done" shows the real chunk count returned by the server.
 */
export default function UploadProgress({ job }: { job: UploadJob }) {
  const steps = [
    { label: "Uploading", done: job.percent >= 100 || job.status !== "uploading", active: job.status === "uploading" },
    {
      label: "Extracting text, generating embeddings & indexing",
      done: job.status === "done",
      active: job.status === "processing",
    },
    { label: job.chunks != null ? `Indexed ${job.chunks} chunks` : "Indexed", done: job.status === "done", active: false },
  ];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-line bg-card p-3"
    >
      <div className="flex items-center gap-2">
        <FileText size={16} className="shrink-0 text-accent" aria-hidden />
        <span className="flex-1 truncate text-sm font-medium text-content">{job.name}</span>
        {job.status === "done" && <CheckCircle2 size={16} className="text-emerald-400" aria-hidden />}
        {job.status === "error" && <AlertCircle size={16} className="text-rose-400" aria-hidden />}
        {(job.status === "uploading" || job.status === "processing") && (
          <Loader2 size={16} className="animate-spin text-accent" aria-hidden />
        )}
      </div>

      {job.status !== "error" ? (
        <>
          <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-card2">
            {job.status === "uploading" ? (
              <div
                className="h-full rounded-full bg-brand-500 transition-[width] duration-200"
                style={{ width: `${job.percent}%` }}
              />
            ) : job.status === "processing" ? (
              // Indeterminate shimmer while the server processes.
              <div className="relative h-full w-full">
                <motion.div
                  className="absolute inset-y-0 w-1/3 rounded-full bg-brand-500"
                  animate={{ x: ["-100%", "300%"] }}
                  transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
                />
              </div>
            ) : (
              <div className="h-full w-full rounded-full bg-emerald-500" />
            )}
          </div>

          <ul className="mt-3 space-y-1.5">
            {steps.map((step, i) => (
              <li key={i} className="flex items-center gap-2 text-xs">
                {step.done ? (
                  <CheckCircle2 size={14} className="text-emerald-400" aria-hidden />
                ) : step.active ? (
                  <Loader2 size={14} className="animate-spin text-accent" aria-hidden />
                ) : (
                  <span className="h-3.5 w-3.5 rounded-full border border-line" aria-hidden />
                )}
                <span className={cn(step.done ? "text-muted" : step.active ? "text-content" : "text-subtle")}>
                  {step.label}
                </span>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="mt-2 text-xs text-rose-300">{job.error ?? "Upload failed."}</p>
      )}
    </motion.div>
  );
}
