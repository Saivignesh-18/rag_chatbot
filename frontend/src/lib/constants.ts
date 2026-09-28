// Must match the backend REFUSAL_MESSAGE exactly (prompt_service.py).
export const REFUSAL_MESSAGE = "I couldn't find this information in the selected documents.";

export function isRefusal(text: string): boolean {
  return text.trim() === REFUSAL_MESSAGE;
}

// Google OAuth client id is public (safe for the browser). Prefer the build-time
// env var, falling back to the provided client id so the app works out of the box.
export const GOOGLE_CLIENT_ID =
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  "319420188294-b74l9ah7q95naq3p45bd4sqqltm6931k.apps.googleusercontent.com";

export const AUTH_TOKEN_KEY = "auth_token";
