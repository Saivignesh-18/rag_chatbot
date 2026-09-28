import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import * as apiClient from "@/services/api";
import { clearToken, setToken, setUnauthorizedHandler } from "@/services/api";
import type { AuthUser } from "@/types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (credential: string) => Promise<void>;
  loginWithPassword: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);

  const applyAuth = useCallback((access_token: string, u: AuthUser) => {
    setToken(access_token);
    setUser(u);
    setStatus("authenticated");
  }, []);

  const login = useCallback(
    async (credential: string) => {
      const { access_token, user: u } = await apiClient.googleLogin(credential);
      applyAuth(access_token, u);
    },
    [applyAuth]
  );

  const loginWithPassword = useCallback(
    async (email: string, password: string) => {
      const { access_token, user: u } = await apiClient.loginEmail(email, password);
      applyAuth(access_token, u);
    },
    [applyAuth]
  );

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const { access_token, user: u } = await apiClient.registerEmail(email, password, name);
      applyAuth(access_token, u);
    },
    [applyAuth]
  );

  const logout = useCallback(async () => {
    await apiClient.logout();
    clearToken();
    setUser(null);
    setStatus("unauthenticated");
    navigate("/login", { replace: true });
  }, [navigate]);

  // Redirect to /login whenever the API reports 401.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setStatus("unauthenticated");
      navigate("/login", { replace: true });
    });
  }, [navigate]);

  // Bootstrap: validate an existing token by loading the profile.
  useEffect(() => {
    let active = true;
    (async () => {
      if (!apiClient.getToken()) {
        setStatus("unauthenticated");
        return;
      }
      try {
        const me = await apiClient.getMe();
        if (!active) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (!active) return;
        clearToken();
        setStatus("unauthenticated");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      isAuthenticated: status === "authenticated",
      login,
      loginWithPassword,
      register,
      logout,
    }),
    [status, user, login, loginWithPassword, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
