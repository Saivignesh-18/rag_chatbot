// Shared API and domain types.

export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  total_chunks: number;
  page_count: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Source {
  document_id: string;
  document_name: string;
  page_number: number | null;
  chunk_id: string;
  similarity_score: number;
}

export interface ChatResponse {
  success: boolean;
  answer: string;
  sources: Source[];
  session_id: string;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  sources?: Source[] | null;
  created_at?: string;
  // Client-only flags:
  pending?: boolean;
  error?: boolean;
}

export interface ChatSession {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  documents: SessionDocument[];
}

export interface Stats {
  documents: number;
  ready_documents: number;
  indexed_chunks: number;
  chat_sessions: number;
  questions: number;
  selected_documents: number;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string | null;
  profile_picture: string | null;
  provider?: string;
  created_at?: string;
}

export interface SessionDocument {
  id: string;
  filename: string;
  file_type: string;
  status: DocumentStatus;
}

export interface ChatSessionDetail {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  documents: SessionDocument[];
}

export interface UploadResponse {
  success: boolean;
  document_id: string;
  filename: string;
  total_chunks: number;
  message: string;
}

export interface ApiError {
  message: string;
  error_code: string;
  status?: number;
}
