import { AnimatePresence } from "framer-motion";
import { UploadCloud } from "lucide-react";
import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useApp } from "@/context/AppContext";
import { toApiError, uploadDocument } from "@/services/api";
import { cn } from "@/lib/utils";
import UploadProgress, { type UploadJob } from "./UploadProgress";

const ALLOWED_EXT = [".pdf", ".docx", ".txt"];
const MAX_MB = 20;

function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

export default function DocumentUpload({ variant = "full" }: { variant?: "full" | "compact" }) {
  const { refreshDocuments, refreshStats, addToast } = useApp();
  const [jobs, setJobs] = useState<UploadJob[]>([]);

  const patchJob = useCallback((id: string, patch: Partial<UploadJob>) => {
    setJobs((prev) => prev.map((j) => (j.id === id ? { ...j, ...patch } : j)));
  }, []);

  const runUpload = useCallback(
    async (file: File) => {
      const id = crypto.randomUUID();
      setJobs((prev) => [...prev, { id, name: file.name, status: "uploading", percent: 0 }]);

      // Client-side pre-validation (backend remains authoritative).
      if (!ALLOWED_EXT.includes(extOf(file.name))) {
        patchJob(id, { status: "error", error: "Unsupported type. Use PDF, DOCX or TXT." });
        return;
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        patchJob(id, { status: "error", error: `File exceeds ${MAX_MB} MB.` });
        return;
      }
      if (file.size === 0) {
        patchJob(id, { status: "error", error: "File is empty." });
        return;
      }

      try {
        const res = await uploadDocument(file, (percent) => {
          patchJob(id, { percent });
          if (percent >= 100) patchJob(id, { status: "processing" });
        });
        patchJob(id, { status: "done", percent: 100, chunks: res.total_chunks });
        addToast("success", `${res.filename} indexed (${res.total_chunks} chunks).`);
        await Promise.all([refreshDocuments(), refreshStats()]);
        // Auto-clear the finished job after a short delay.
        window.setTimeout(() => setJobs((prev) => prev.filter((j) => j.id !== id)), 3500);
      } catch (err) {
        patchJob(id, { status: "error", error: toApiError(err).message });
      }
    },
    [addToast, patchJob, refreshDocuments, refreshStats]
  );

  const onDrop = useCallback(
    (accepted: File[]) => {
      accepted.forEach((file) => void runUpload(file));
    },
    [runUpload]
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "text/plain": [".txt"],
    },
    multiple: true,
    noClick: variant === "compact",
    noKeyboard: variant === "compact",
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          "group cursor-pointer rounded-2xl border-2 border-dashed p-5 text-center transition",
          isDragActive
            ? "border-brand-400 bg-brand-500/10"
            : "border-line bg-card hover:border-brand-400/60 hover:bg-card"
        )}
        aria-label="Upload documents. Drag and drop PDF, DOCX or TXT files, or activate to browse."
      >
        <input {...getInputProps()} aria-hidden />
        <div className="flex flex-col items-center gap-2">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-500/15 text-accent transition group-hover:scale-105">
            <UploadCloud size={22} aria-hidden />
          </span>
          <p className="text-sm font-medium text-content">
            {isDragActive ? "Drop to upload" : "Drag & drop or click to upload"}
          </p>
          <p className="text-xs text-subtle">PDF, DOCX, TXT · up to {MAX_MB} MB</p>
          {variant === "compact" && (
            <button
              type="button"
              onClick={open}
              className="mt-1 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-500"
            >
              Browse files
            </button>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <AnimatePresence>
          {jobs.map((job) => (
            <UploadProgress key={job.id} job={job} />
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
