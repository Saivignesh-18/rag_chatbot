import axios, { AxiosError, type AxiosProgressEvent } from "axios";
import { AUTH_TOKEN_KEY } from "@/lib/constants";
import type {
  ApiError,
  AuthUser,
  ChatResponse,
  ChatSession,
  ChatSessionDetail,
  ChatMessage,
  DocumentItem,
  Stats,
  UploadResponse,
} from "@/types";

// When VITE_API_BASE_URL is empty we use same-origin requests (Vite dev proxy
// forwards /api -> backend; nginx does the same in production).
const BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

export const api = axios.create({ baseURL: BASE_URL });

// ---- Token storage ----
export function getToken(): string | null {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}
export function setToken(token: string): void {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

// ---- Interceptors ----
// Attach the Bearer token to every request.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401, clear the token and notify the app to redirect to /login.
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}
api.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken();
      // Avoid loops on the login endpoint itself.
      const url = error.config?.url ?? "";
      if (!url.includes("/auth/")) onUnauthorized?.();
    }
    return Promise.reject(error);
  }
);

export function toApiError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const axiosErr = err as AxiosError<{ message?: string; error_code?: string }>;
    const data = axiosErr.response?.data;
    if (data?.message) {
      return { message: data.message, error_code: data.error_code ?? "ERROR", status: axiosErr.response?.status };
    }
    if (axiosErr.code === "ERR_NETWORK") {
      return { message: "Cannot reach the server. Is the backend running?", error_code: "NETWORK_ERROR" };
    }
    return { message: axiosErr.message || "Request failed.", error_code: "ERROR", status: axiosErr.response?.status };
  }
  return { message: "An unexpected error occurred.", error_code: "UNKNOWN" };
}

// ---- Auth ----
type AuthResult = { access_token: string; user: AuthUser };

export async function googleLogin(credential: string): Promise<AuthResult> {
  const { data } = await api.post<AuthResult>("/api/auth/google", { credential });
  return data;
}
export async function registerEmail(email: string, password: string, name: string): Promise<AuthResult> {
  const { data } = await api.post<AuthResult>("/api/auth/register", { email, password, name });
  return data;
}
export async function loginEmail(email: string, password: string): Promise<AuthResult> {
  const { data } = await api.post<AuthResult>("/api/auth/login", { email, password });
  return data;
}
export async function forgotPassword(email: string): Promise<{ message: string; reset_token: string | null }> {
  const { data } = await api.post<{ message: string; reset_token: string | null }>(
    "/api/auth/forgot-password",
    { email }
  );
  return data;
}
export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const { data } = await api.post<{ message: string }>("/api/auth/reset-password", {
    token,
    new_password: newPassword,
  });
  return data;
}
export async function getMe(): Promise<AuthUser> {
  const { data } = await api.get<{ user: AuthUser }>("/api/auth/me");
  return data.user;
}
export async function logout(): Promise<void> {
  try {
    await api.post("/api/auth/logout");
  } catch {
    // Ignore; logout is client-side regardless.
  }
}

// ---- Stats ----
export async function getStats(): Promise<Stats> {
  const { data } = await api.get<Stats>("/api/stats");
  return data;
}

// ---- Documents ----
export async function listDocuments(): Promise<DocumentItem[]> {
  const { data } = await api.get<{ documents: DocumentItem[] }>("/api/documents");
  return data.documents;
}
export async function getDocument(id: string): Promise<DocumentItem> {
  const { data } = await api.get<{ document: DocumentItem }>(`/api/documents/${id}`);
  return data.document;
}
export async function uploadDocument(file: File, onProgress?: (percent: number) => void): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  // Let the browser set Content-Type (incl. the multipart boundary) automatically.
  const { data } = await api.post<UploadResponse>("/api/documents/upload", form, {
    onUploadProgress: (evt: AxiosProgressEvent) => {
      if (onProgress && evt.total) onProgress(Math.round((evt.loaded / evt.total) * 100));
    },
  });
  return data;
}
export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/api/documents/${id}`);
}
export function documentFileUrl(id: string): string {
  // Includes the token so inline PDF preview (opened in a new tab) is authorized.
  const token = getToken();
  const q = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${BASE_URL}/api/documents/${id}/file${q}`;
}

// ---- Chat sessions ----
export async function createSession(documentIds: string[], title?: string): Promise<ChatSessionDetail> {
  const { data } = await api.post<{ session: ChatSessionDetail }>("/api/chat/sessions", {
    document_ids: documentIds,
    title: title ?? null,
  });
  return data.session;
}
export async function updateSessionScope(sessionId: string, documentIds: string[]): Promise<ChatSessionDetail> {
  const { data } = await api.patch<{ session: ChatSessionDetail }>(
    `/api/chat/sessions/${sessionId}/documents`,
    { document_ids: documentIds }
  );
  return data.session;
}
export async function listSessions(): Promise<ChatSession[]> {
  const { data } = await api.get<{ sessions: ChatSession[] }>("/api/chat/sessions");
  return data.sessions;
}
export async function getSession(id: string): Promise<{ session: ChatSessionDetail; messages: ChatMessage[] }> {
  const { data } = await api.get<{ session: ChatSessionDetail; messages: ChatMessage[] }>(
    `/api/chat/sessions/${id}`
  );
  return { session: data.session, messages: data.messages };
}
export async function deleteSession(id: string): Promise<void> {
  await api.delete(`/api/chat/sessions/${id}`);
}

// ---- Chat ----
export async function sendChat(sessionId: string, question: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/api/chat", { session_id: sessionId, question });
  return data;
}
