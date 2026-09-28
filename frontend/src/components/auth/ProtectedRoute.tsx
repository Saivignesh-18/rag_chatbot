import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

/** Gate authenticated areas. Shows a loader while the session is verified. */
export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-bg">
        <div className="flex items-center gap-3 text-muted">
          <Loader2 size={22} className="animate-spin text-accent" aria-hidden />
          <span className="text-sm">Loading your workspace...</span>
        </div>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
