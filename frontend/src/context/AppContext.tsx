import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as apiClient from "@/services/api";
import { toApiError } from "@/services/api";
import type { DocumentItem, Stats } from "@/types";

export type ToastType = "success" | "error" | "info";
export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

interface AppContextValue {
  // Documents
  documents: DocumentItem[];
  documentsLoading: boolean;
  documentsError: string | null;
  refreshDocuments: () => Promise<void>;
  removeDocument: (id: string) => Promise<void>;
  uploadFile: (file: File) => Promise<boolean>;

  // Stats
  stats: Stats;
  refreshStats: () => Promise<void>;

  // Toasts
  toasts: Toast[];
  addToast: (type: ToastType, message: string) => void;
  dismissToast: (id: string) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

const EMPTY_STATS: Stats = {
  documents: 0,
  ready_documents: 0,
  indexed_chunks: 0,
  chat_sessions: 0,
  questions: 0,
  selected_documents: 0,
};

export function AppProvider({ children }: { children: ReactNode }) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats>(EMPTY_STATS);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, type, message }]);
      window.setTimeout(() => dismissToast(id), 5000);
    },
    [dismissToast]
  );

  const refreshStats = useCallback(async () => {
    try {
      setStats(await apiClient.getStats());
    } catch {
      // Stats are non-critical; ignore failures silently.
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    setDocumentsError(null);
    try {
      setDocuments(await apiClient.listDocuments());
    } catch (err) {
      setDocumentsError(toApiError(err).message);
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  const uploadFile = useCallback(
    async (file: File): Promise<boolean> => {
      try {
        const res = await apiClient.uploadDocument(file);
        addToast("success", `${res.filename} indexed (${res.total_chunks} chunks).`);
        await Promise.all([refreshDocuments(), refreshStats()]);
        return true;
      } catch (err) {
        addToast("error", toApiError(err).message);
        return false;
      }
    },
    [addToast, refreshDocuments, refreshStats]
  );

  const removeDocument = useCallback(
    async (id: string) => {
      try {
        await apiClient.deleteDocument(id);
        setDocuments((prev) => prev.filter((d) => d.id !== id));
        addToast("success", "Document deleted.");
        void refreshStats();
      } catch (err) {
        addToast("error", toApiError(err).message);
      }
    },
    [addToast, refreshStats]
  );

  // Data is loaded on demand by authenticated pages (not on mount), so the
  // provider can wrap the whole app including the public login page.

  const value = useMemo<AppContextValue>(
    () => ({
      documents,
      documentsLoading,
      documentsError,
      refreshDocuments,
      removeDocument,
      uploadFile,
      stats,
      refreshStats,
      toasts,
      addToast,
      dismissToast,
    }),
    [
      documents,
      documentsLoading,
      documentsError,
      refreshDocuments,
      removeDocument,
      uploadFile,
      stats,
      refreshStats,
      toasts,
      addToast,
      dismissToast,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
