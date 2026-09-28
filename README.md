# AI Document Assistant — Document-Only RAG Chatbot

A production-quality Retrieval-Augmented Generation (RAG) chatbot that answers
questions **only** from documents you upload. It never falls back to the LLM's
general knowledge: if the answer is not in your selected documents, it says so.

> Sign in with Google → upload PDF / DOCX / TXT → **select the documents to chat with** →
> ask questions → get grounded answers **with source citations**.

Multi-user: each account sees only its own documents and chats. Every chat is
scoped to a chosen set of documents, and retrieval searches **only those**.

---

## 1. Project Overview

- **Google sign-in** (Google Identity Services); the backend verifies the Google ID
  token and issues its own JWT. Each user's documents and chats are isolated.
- Upload documents (PDF, DOCX, TXT). Documents are parsed, cleaned, chunked,
  embedded, and stored in PostgreSQL + pgvector, owned by the uploading user.
- **Selective-document RAG:** a chat session is scoped to a chosen set of documents.
  Vector search is restricted **at the database-query level** to those documents
  (and the owner) — unselected documents can never influence an answer.
- A configurable **similarity threshold** gates retrieval: if nothing is relevant
  enough, the assistant refuses instead of hallucinating (no LLM call).
- Relevant chunks are passed to the **Groq LLM** with a strict document-only system
  prompt. Answers include verifiable citations (document name + page number).

## 2. Architecture

```
          Upload (PDF/DOCX/TXT)
                  │
                  ▼
        Document Parser → Clean → Chunk
                  │
                  ▼
        Embeddings (local, configurable)
                  │
                  ▼
        PostgreSQL + pgvector  ◄─────────────┐
                                             │
User question ──► Embedding ──► Vector search┘
                  │
                  ▼
        Top-K chunks ──► Similarity threshold
                  │                 │
             (relevant)        (not relevant)
                  │                 │
                  ▼                 ▼
        Context builder     "I couldn't find this
                  │          information in the
                  ▼          provided documents."
             Groq LLM
                  │
                  ▼
        Grounded answer + source citations
```

## 3. Technology Stack

**Backend:** Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn, python-dotenv
**Vector DB:** PostgreSQL + pgvector
**Embeddings:** `fastembed` (local ONNX models, no extra API key) — configurable
**LLM:** Groq API (primary) with automatic Google **Gemini** fallback, behind a provider router
**Parsing:** pypdf (PDF, page-aware), python-docx (DOCX), UTF-8 text (TXT)
**Frontend:** React, TypeScript, Vite, Tailwind CSS, React Router, Axios, Framer Motion, Lucide, Recharts

## 4. Prerequisites

- Python 3.11+ (tested on 3.13)
- Node.js 18+ (tested on 20/24)
- Docker + Docker Compose (recommended, for PostgreSQL + pgvector)
- A Groq API key: https://console.groq.com/keys

## 5. Virtual Environment Setup

```bash
python -m venv .venv
```

Activate it:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Windows CMD: `.venv\Scripts\activate`
- macOS / Linux: `source .venv/bin/activate`

Then:

```bash
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

## 6. Environment Variables

Copy `.env.example` to `.env` and fill in values (at minimum `GROQ_API_KEY`).

| Variable | Description | Example |
| --- | --- | --- |
| `GROQ_API_KEY` | Groq API key (backend only, never commit) | `gsk_...` |
| `DATABASE_URL` | SQLAlchemy Postgres URL | `postgresql+psycopg2://raguser:ragpassword@localhost:5433/ragdb` |
| `GROQ_MODEL` | Groq model id (primary LLM) | `openai/gpt-oss-20b` |
| `GEMINI_API_KEY` | Google Gemini key (backend only; fallback LLM) | `AQ...` / `AIza...` |
| `GEMINI_MODEL` | Gemini model id | `gemini-flash-latest` |
| `PRIMARY_LLM` | Which provider is tried first | `groq` |
| `FALLBACK_LLM` | Provider used on transient failure | `gemini` |
| `ENABLE_LLM_FALLBACK` | Turn automatic fallback on/off | `true` |
| `GOOGLE_CLIENT_ID` | Google OAuth client id (public; also used by the frontend) | `3194...apps.googleusercontent.com` |
| `JWT_SECRET_KEY` | Secret for signing app JWTs (backend only, keep secret) | long random string |
| `EMBEDDING_MODEL` | fastembed model id | `BAAI/bge-small-en-v1.5` |
| `CHUNK_SIZE` | Characters per chunk | `1000` |
| `CHUNK_OVERLAP` | Overlap between chunks | `200` |
| `TOP_K` | Chunks retrieved per query | `5` |
| `SIMILARITY_THRESHOLD` | Min cosine similarity to answer | `0.5` (tune!) |
| `MAX_FILE_SIZE_MB` | Max upload size | `20` |
| `CORS_ORIGINS` | Allowed origins (comma separated) | `http://localhost:3000` |

Secrets (`GROQ_API_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`) exist only on the backend
and are never sent to the frontend or committed to git. Only `GOOGLE_CLIENT_ID`
(which is public by design) is used by the browser.

The frontend can optionally set `VITE_GOOGLE_CLIENT_ID` (see `frontend/.env.example`);
if unset it falls back to the configured client id.

### Authentication & selective-document RAG

Two ways to sign in:

- **Email / password:** `POST /api/auth/register` (name, email, password ≥ 8 chars)
  and `POST /api/auth/login`. Passwords are hashed with **bcrypt**. Forgot-password:
  `POST /api/auth/forgot-password` issues a reset token and `POST /api/auth/reset-password`
  sets a new one. *(No email service is configured, so the reset token is returned by
  the API for local/dev use — in production, email it instead of returning it.)*
- **Google:** the browser gets a Google ID token via Google Identity Services and
  posts it to `POST /api/auth/google`. The backend **verifies the token with Google**
  (signature, audience, issuer, expiry), finds/creates the user by the stable Google
  `sub` (linking to an existing email account when the address matches), and returns an
  app **JWT** used as a `Bearer` token for all other calls.

Both paths return the same app JWT, and all other APIs are identical afterwards.
- **Isolation:** every document and chat session belongs to a `user_id`. All document
  and chat APIs require authentication and are scoped to the current user. Cross-user
  access returns 404/403.
- **Selective retrieval:** you select documents on the Documents page and start a chat.
  The session's document scope is stored in `chat_session_documents`. The chat request
  only sends `{ session_id, question }` — the backend reads the selected document IDs
  **from the database** and restricts the pgvector search to `WHERE user_id = :me AND
  document_id IN (:selected)`. Unselected documents cannot influence answers.

> **Google Cloud setup:** add your frontend origin (e.g. `http://localhost:3000`) as an
> **Authorized JavaScript origin** for the OAuth client in the Google Cloud console,
> otherwise the Google button will not render/sign in.

## 7. PostgreSQL Setup

The easiest path is Docker (see section 12). For local (non-Docker) development you
can run just the database in a container:

```bash
docker run -d --name rag_postgres \
  -e POSTGRES_USER=raguser -e POSTGRES_PASSWORD=ragpassword -e POSTGRES_DB=ragdb \
  -p 5433:5432 pgvector/pgvector:pg16
```

> **Why host port 5433?** Many machines already run PostgreSQL on the default
> `5432`. To avoid clashes, this project maps the container's `5432` to host
> **`5433`** everywhere host-facing. Inside Docker Compose the backend still talks
> to the database on the internal `5432`. If you prefer `5432`, change
> `DATABASE_URL` and the compose port mapping accordingly.

To use your own PostgreSQL, create a database and user matching your `DATABASE_URL`.

## 8. pgvector Setup

The application requires the `vector` extension. With the provided Docker image
(`pgvector/pgvector:pg16`) it is available automatically and enabled by
`backend/app/db/migrations/init.sql`. On a manual install run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 9. Backend Setup

Make sure PostgreSQL is running (section 7) and `.env` is filled in, then:

```bash
# from the project root, with the venv active
uvicorn app.main:app --reload --app-dir backend
```

API docs: http://localhost:8000/docs

> The first document upload / question downloads the local embedding model
> (~one-time, cached afterwards), so it can take a little longer than usual.

## 10. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

## 11. Running the Application

1. Start PostgreSQL (Docker or local).
2. Start the backend (`uvicorn ...`).
3. Start the frontend (`npm run dev`).
4. Open http://localhost:3000, upload a document, and start asking questions.

## 12. Docker Setup

With Docker Desktop running and `.env` populated (at least `GROQ_API_KEY`):

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- PostgreSQL: localhost:5433 (container internal 5432)

Services:

- **postgres** — `pgvector/pgvector:pg16`, extension enabled on first init.
- **backend** — FastAPI (Uvicorn). Reads `GROQ_API_KEY` from `.env` (git-ignored);
  `DATABASE_URL` is overridden to the internal `postgres:5432`.
- **frontend** — production React build served by nginx, which reverse-proxies
  `/api` to the backend (so the browser never needs the key or CORS).

The embedding model is cached in the `fastembed_cache` volume; database data lives
in the `postgres_data` volume.

## 13. API Documentation

Interactive docs at `/docs`. All endpoints except `/api/health` and
`/api/auth/google` require a `Bearer` token. Key endpoints:

Auth:
- `POST /api/auth/register` · `POST /api/auth/login` — email/password (returns app JWT)
- `POST /api/auth/forgot-password` · `POST /api/auth/reset-password` — password reset
- `POST /api/auth/google` — verify a Google ID token, return app JWT + user
- `GET /api/auth/me` — current user profile · `POST /api/auth/logout`

Documents (user-scoped):
- `POST /api/documents/upload` · `GET /api/documents` · `GET /api/documents/{id}`
- `GET /api/documents/{id}/file` — download/preview the stored original
- `DELETE /api/documents/{id}`

Chat (user-scoped, session-driven):
- `POST /api/chat/sessions` `{ document_ids, title? }` — create a scoped session
- `PATCH /api/chat/sessions/{id}/documents` `{ document_ids }` — change scope (keeps history)
- `GET /api/chat/sessions` · `GET /api/chat/sessions/{id}` · `DELETE /api/chat/sessions/{id}`
- `POST /api/chat` `{ session_id, question }` — ask (grounded answer + sources)

Misc: `GET /api/stats` (per-user counts) · `GET /api/health`

Frontend routes: `/login`, `/app/home`, `/app/documents`, `/app/chat/:sessionId`
(all `/app/*` routes require authentication).

All examples below require an auth token: `-H "Authorization: Bearer $TOKEN"`
(obtained from `POST /api/auth/google`).

### Example: upload a document

```bash
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@requirements.pdf;type=application/pdf" \
  http://localhost:3000/api/documents/upload
```

```json
{
  "success": true,
  "document_id": "677cb310-c261-4879-ae0f-b285d3315fb7",
  "filename": "requirements.pdf",
  "total_chunks": 125,
  "message": "Document processed successfully"
}
```

### Example: create a scoped session, then ask

```bash
# 1) Create a chat session scoped to the selected document(s)
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"document_ids":["<doc-id-1>","<doc-id-2>"]}' \
  http://localhost:3000/api/chat/sessions

# 2) Ask a question in that session (scope comes from the DB, not the request)
curl -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"session_id":"<session-id>","question":"How many concurrent users are supported?"}' \
  http://localhost:3000/api/chat
```

```json
{
  "success": true,
  "answer": "The system supports **600 concurrent users under normal conditions** and **3,000 concurrent users during peak periods**.",
  "sources": [
    { "document_id": "677cb310-...", "document_name": "requirements.pdf", "page_number": 2, "chunk_id": "…", "similarity_score": 0.71 }
  ],
  "session_id": "…"
}
```

When nothing relevant is found in the selected documents, the answer is exactly:

```json
{ "success": true, "answer": "I couldn't find this information in the selected documents.", "sources": [] }
```

Errors use a consistent envelope and never leak stack traces:

```json
{ "success": false, "message": "Unsupported file type. Allowed types: PDF, DOCX, TXT.", "error_code": "UNSUPPORTED_FILE_TYPE" }
```

## 14. RAG Pipeline Explanation

See section 2. The threshold gate is enforced in code (not just the prompt), so an
irrelevant question returns the standard refusal even before the LLM is called.

### LLM providers & automatic fallback

The generation step uses a provider **router**, not a single hard-coded provider:

```
RAG retrieval → document-only prompt → LLM Router
                                          ├── Groq (primary)  → answer
                                          └── Gemini (fallback on transient failure)
```

- **Primary = Groq**, **fallback = Gemini** (`PRIMARY_LLM` / `FALLBACK_LLM`).
- The router falls back **only on transient provider failures** — HTTP 429 / rate
  limit, timeouts, and temporary 5xx/service-unavailable. Application errors (auth,
  unknown model, malformed request, empty response) are **not** retried.
- The document-only prompt (system instruction + retrieved, selected-document
  context) is built **once** and handed to the router, so Groq and Gemini receive
  **identical** context. Fallback never re-runs retrieval, never broadens scope, and
  never bypasses user/document isolation. The refusal message is unchanged.
- If both providers fail, the API returns a controlled
  *"Sorry, the AI service is temporarily unavailable"* error (no stack traces / keys).
- Disable fallback with `ENABLE_LLM_FALLBACK=false` (Groq-only).
- Keys are backend-only and never logged or sent to the frontend; the frontend still
  calls just `POST /api/chat` and is unaware of which provider answered.

## 15. Security Considerations

- **Google ID tokens are verified server-side**; identity comes only from verified
  claims (never from values the client sends). App JWTs are signed with `JWT_SECRET_KEY`.
- **Per-user isolation** — documents and chat sessions are owned by `user_id`; all
  APIs are authenticated and scoped. Cross-user access returns 404/403.
- **Selective scope is server-authoritative** — selected document IDs are read from
  the database by `session_id`, never trusted from the chat request; ownership of
  selected documents is validated.
- Secrets via environment variables only; `.env` is git-ignored. Only the public
  `GOOGLE_CLIENT_ID` reaches the browser.
- CORS restricted to configured origins.
- File type + size validation; filenames sanitised.
- Parameterised queries via SQLAlchemy ORM.
- Errors are sanitised — no stack traces leak to clients.
- Basic rate limiting on API endpoints.

## 16. Testing Instructions

The tests exercise the real pipeline (real parsing, real embeddings, real
PostgreSQL + pgvector). A database must be reachable at your `DATABASE_URL`, so
start one first:

```bash
# start just the database (or use your local docker rag_postgres from section 7)
docker compose up -d postgres
```

Then run the suite:

```bash
cd backend
pytest -q
```

What is covered:

- **Auth** — Google login creates/reuses a user (no duplicates), `/me`, logout,
  invalid-token rejection, protected-route 401s.
- **Documents** — valid PDF/DOCX/TXT, invalid type, empty, oversized, corrupted,
  full list/get/delete lifecycle (authenticated, user-scoped).
- **RAG & selective retrieval** — relevant question (LLM + sources), irrelevant
  question (refused **without** calling the LLM), multi-document retrieval,
  similarity-threshold gate, session history, and **document isolation** (Doc A says
  the retirement age is 60, Doc B says 58 — scoping to A answers 60, to B answers 58,
  to a third document refuses), plus scope-change preserving history.
- **User isolation** — users only see their own documents/sessions; cross-user
  document/session access is blocked; a session cannot be scoped to another user's
  document; retrieval never crosses users.
- **Groq** — success, empty/malformed response, timeout, rate limit, connection
  failure, model-not-found, auth (all mapped to sanitised errors; no key leakage).
- **Security** — filename sanitisation/path-traversal, size/type limits, invalid
  input, and secret non-exposure.

The live evaluation in `tests/test_evaluation.py` uses the real Groq API and is
skipped automatically when `GROQ_API_KEY` is not set.

### Critical evaluation (grounding check)

With a document stating *"600 concurrent users … 3,000 concurrent users during peak
periods"*:

- **"How many concurrent users are supported?"** → answered from the document
  (mentions 600 and 3,000) with citations.
- **"Who is the Prime Minister of India?"** → *"I couldn't find this information in
  the selected documents."* (no general-knowledge answer).

## 17. Troubleshooting

- **`vector` type does not exist** — ensure the pgvector extension is enabled
  (`CREATE EXTENSION IF NOT EXISTS vector;`). The provided image does this
  automatically.
- **Port 5432 already in use** — a local PostgreSQL is likely running; this project
  uses host port **5433** to avoid the clash (see section 7).
- **Groq `model_unavailable` / `decommissioned`** — Groq rotates models. Set
  `GROQ_MODEL` to a currently supported model (default: `openai/gpt-oss-20b`; see
  https://console.groq.com/docs/models).
- **Assistant always refuses** — your `SIMILARITY_THRESHOLD` is likely too high for
  the embedding model. For the default `BAAI/bge-small-en-v1.5`, ~`0.45`–`0.60`
  works well; tune against your own evaluation questions.
- **First request is slow** — the embedding model downloads once on first use, then
  is cached.
- **Empty answers from a reasoning model** — reasoning models (e.g. `gpt-oss`) spend
  completion tokens on reasoning; keep `groq_max_tokens` comfortably high (default
  2048).
- **Google `Error 400: origin_mismatch`** — the frontend origin is not authorized for
  the OAuth client. In the Google Cloud console → APIs & Services → Credentials → your
  OAuth client → **Authorized JavaScript origins**, add `http://localhost:3000` (and any
  other origin you serve from). Meanwhile you can use **email/password** sign-in, which
  needs no Google configuration. `GET /api/health` shows `google_auth_configured`.
- **Signed out unexpectedly / 401 loops** — the app JWT expired or `JWT_SECRET_KEY`
  changed; sign in again. Tokens are stored in the browser and cleared on logout.
- **Gemini `404 ... no longer available to new users`** — pinned model names (e.g.
  `gemini-2.5-flash`) may be unavailable to a given key. Use `GEMINI_MODEL=gemini-flash-latest`
  (or run `client.models.list()` to see what your key can access). A one-off Gemini
  `503 high demand` is transient — the router treats it as a provider failure.

---

Built as a document-grounded RAG assistant: **accuracy, security, traceability, and
document grounding first.**
