# Deploying to Render

This app deploys as three Render resources, defined in [`render.yaml`](./render.yaml):

| Resource | Type | Notes |
| --- | --- | --- |
| `rag-db` | Managed PostgreSQL | pgvector is enabled automatically by the backend on startup |
| `rag-backend` | Docker web service | FastAPI (`backend/Dockerfile`) |
| `rag-frontend` | Static site | React/Vite build served on Render's CDN |

The frontend (in the browser) calls the backend directly, so the backend must
allow the frontend origin via CORS, and the frontend must be built with the
backend URL. Those two values are the only manual wiring.

---

## 1. Push the project to GitHub

The project isn't a git repo yet. From the project root:

```bash
git init
git add .
git commit -m "Prepare for Render deployment"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

`.env` is already git-ignored, so your secrets won't be committed. Verify with
`git status` that `.env` is **not** listed.

## 2. Create the Blueprint on Render

1. In the [Render dashboard](https://dashboard.render.com), click **New → Blueprint**.
2. Connect the GitHub repo you just pushed. Render detects `render.yaml`.
3. Render shows the three resources and prompts for every `sync: false` value:
   - `GROQ_API_KEY` - your Groq key (from console.groq.com)
   - `GEMINI_API_KEY` - your Google AI Studio key
   - `GOOGLE_CLIENT_ID` - your Google OAuth client ID (same value for backend and frontend)
   - `CORS_ORIGINS` (backend) - enter `https://rag-frontend.onrender.com`
   - `VITE_API_BASE_URL` (frontend) - enter `https://rag-backend.onrender.com`
   - `VITE_GOOGLE_CLIENT_ID` (frontend) - your Google OAuth client ID
4. Click **Apply**. Render provisions the database, builds the backend image, and
   builds the static frontend.

> The URLs follow the pattern `https://<service-name>.onrender.com`. If a name was
> already taken, Render appends a suffix. After the first deploy, check the real
> URLs on each service's page and, if they differ, fix `CORS_ORIGINS` and
> `VITE_API_BASE_URL` (see step 4).

## 3. Configure Google OAuth

In Google Cloud Console → **APIs & Services → Credentials → your OAuth client**,
add the frontend URL under **Authorized JavaScript origins**:

```
https://rag-frontend.onrender.com
```

Without this, the Google sign-in button will fail (email/password still works).

## 4. Correct the URLs if needed, then redeploy

If the real URLs differ from the guesses in step 2:

- **Backend** → Environment → set `CORS_ORIGINS` to the real frontend URL → save.
- **Frontend** → Environment → set `VITE_API_BASE_URL` to the real backend URL →
  **Manual Deploy → Deploy latest commit** (Vite bakes this value at build time, so
  the frontend must rebuild).

## 5. Verify

- `https://rag-backend.onrender.com/api/health` returns JSON with `"status":"healthy"`.
- Open the frontend URL, register an account, upload a small document, and chat.

---

## Notes, limits, and tuning

**Free tier caveats (change `plan:` in `render.yaml` to upgrade):**

- **Backend RAM (512 MB).** The local embedding model (`bge-small`) is CPU/RAM
  heavy. Small documents are fine, but a large PDF (hundreds of chunks) can run
  out of memory. If indexing fails or the instance restarts mid-upload, bump the
  backend to `plan: 1c-2g` (2 GB).
- **Backend cold starts.** Free services sleep after ~15 min idle. The first
  request afterward is slow because the embedding model re-downloads (~130 MB).
- **Free Postgres is temporary.** Render removes free databases after ~30 days.
  Use a paid `plan:` to keep your data.
- **Ephemeral storage.** Uploaded originals are stored on the container's disk at
  `/app/storage` and are lost on every deploy/restart. Chat still works (chunks
  live in Postgres), but the "view source" PDF preview breaks. To persist them,
  attach a disk (paid) and point storage + model cache at it:

  ```yaml
  #   (under the rag-backend service)
  disk:
    name: data
    mountPath: /app/data
    sizeGB: 1
  envVars:
    - key: UPLOAD_STORAGE_DIR
      value: /app/data/storage
    - key: FASTEMBED_CACHE_PATH
      value: /app/data/.fastembed_cache
  ```

  A disk also fixes cold-start model re-downloads. (Services with a disk can't
  auto-scale beyond one instance - fine for this app.)

**Region.** `rag-backend` and `rag-db` must share a region (both `oregon` here) so
the backend reaches the database over Render's private network.

**Schema.** No migration step is needed - on startup the backend runs
`CREATE EXTENSION IF NOT EXISTS vector` and creates all tables.
