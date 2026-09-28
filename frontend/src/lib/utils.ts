import { clsx, type ClassValue } from "clsx";

/** Merge class names conditionally. */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/** Human-readable file size. */
export function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(value >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

/** Relative-ish date formatting (e.g. "2h ago", "Mar 3"). */
export function formatDate(iso?: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const min = Math.round(diffMs / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Format a 0..1 similarity as a percentage. */
export function formatRelevance(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Compact number formatting for the dashboard (1,240). */
export function formatCount(n: number): string {
  return n.toLocaleString();
}

const FILE_TYPE_LABELS: Record<string, string> = {
  pdf: "PDF",
  docx: "DOCX",
  txt: "TXT",
};

export function fileTypeLabel(fileType: string): string {
  return FILE_TYPE_LABELS[fileType] ?? fileType.toUpperCase();
}
