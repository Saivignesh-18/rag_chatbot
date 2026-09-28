import { useCallback, useEffect, useState } from "react";
import { deleteSession, listSessions, toApiError } from "@/services/api";
import { useApp } from "@/context/AppContext";
import type { ChatSession } from "@/types";

export function useSessions() {
  const { addToast } = useApp();
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  const refresh = useCallback(async () => {
    try {
      setSessions(await listSessions());
    } catch {
      // History is non-critical; ignore.
    }
  }, []);

  const remove = useCallback(
    async (id: string) => {
      try {
        await deleteSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
      } catch (err) {
        addToast("error", toApiError(err).message);
      }
    },
    [addToast]
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { sessions, refresh, remove };
}
