import { GoogleLogin } from "@react-oauth/google";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  FileText,
  Loader2,
} from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { forgotPassword, resetPassword, toApiError } from "@/services/api";
import { cn } from "@/lib/utils";

type Mode = "login" | "register" | "forgot" | "reset";

const COPY: Record<Mode, { title: string; subtitle: string; cta: string }> = {
  login: {
    title: "Sign In to Account",
    subtitle: "Enter your credentials to access your workspace.",
    cta: "Sign In",
  },
  register: {
    title: "Sign Up Account",
    subtitle: "Enter your personal data to create your account.",
    cta: "Sign Up",
  },
  forgot: {
    title: "Reset your password",
    subtitle: "Enter your email and we'll get you a reset token.",
    cta: "Send reset token",
  },
  reset: {
    title: "Set a new password",
    subtitle: "Choose a strong new password for your account.",
    cta: "Update password",
  },
};

const STEPS = ["Sign up your account", "Set up your workspace", "Set up your profile"];

const inputCls =
  "w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 transition focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-400/30";

function Labeled({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}

export default function LoginPage({ initialMode = "login" }: { initialMode?: Mode }) {
  const { status, login, loginWithPassword, register } = useAuth();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showPw2, setShowPw2] = useState(false);

  if (status === "authenticated") return <Navigate to="/app/home" replace />;

  const switchMode = (m: Mode) => {
    setMode(m);
    setError(null);
    setInfo(null);
  };

  const guard = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(toApiError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const onGoogle = (credential?: string) =>
    guard(async () => {
      if (!credential) throw new Error("Google did not return a credential.");
      await login(credential);
    });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (mode === "login") {
      void guard(() => loginWithPassword(email, password));
    } else if (mode === "register") {
      if (password.length < 8) return setError("Password must be at least 8 characters.");
      const fullName = `${firstName} ${lastName}`.trim() || email.split("@")[0];
      void guard(() => register(email, password, fullName));
    } else if (mode === "forgot") {
      void guard(async () => {
        const res = await forgotPassword(email);
        if (res.reset_token) {
          setResetToken(res.reset_token);
          switchMode("reset");
          setInfo("Reset token generated (dev mode). Set your new password below.");
        } else {
          setInfo(res.message);
        }
      });
    } else if (mode === "reset") {
      if (password.length < 8) return setError("Password must be at least 8 characters.");
      if (password !== confirm) return setError("Passwords do not match.");
      void guard(async () => {
        await resetPassword(resetToken, password);
        setPassword("");
        setConfirm("");
        switchMode("login");
        setInfo("Password updated. Please sign in.");
      });
    }
  };

  const c = COPY[mode];
  const year = new Date().getFullYear();

  return (
    <div className="flex min-h-screen bg-brand-50 text-slate-900">
      {/* Left: brand / sage panel / steps */}
      <div className="relative hidden w-1/2 overflow-hidden lg:block">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-100 via-brand-50 to-brand-200" />
        <div className="absolute inset-0 bg-grid-pattern opacity-60" />
        <div className="absolute -top-24 left-1/3 h-[30rem] w-[30rem] -translate-x-1/2 rounded-full bg-brand-300/40 blur-[130px]" />
        <div className="absolute bottom-0 right-0 h-72 w-72 rounded-full bg-brand-400/25 blur-[120px]" />

        <div className="relative flex h-full flex-col justify-between p-10 xl:p-14">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-white shadow-sm ring-1 ring-brand-200">
              <FileText size={17} className="text-brand-600" aria-hidden />
            </span>
            <span className="font-display text-sm font-semibold tracking-wide text-brand-900">
              Document AI
            </span>
          </div>

          <div className="max-w-sm">
            <h2 className="font-display text-3xl font-bold tracking-tight text-brand-900 xl:text-4xl">
              Get Started with Us
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-brand-800/80">
              Complete these easy steps to set up your private document workspace.
            </p>

            <div className="mt-8 space-y-3">
              {STEPS.map((step, i) => {
                const active = i === 0;
                return (
                  <div
                    key={step}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-4 py-3.5 text-sm font-medium transition",
                      active
                        ? "bg-white text-brand-900 shadow-card ring-1 ring-brand-200"
                        : "border border-brand-200/70 bg-white/50 text-brand-800"
                    )}
                  >
                    <span
                      className={cn(
                        "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                        active ? "bg-brand-600 text-white" : "bg-brand-200/70 text-brand-700"
                      )}
                    >
                      {i + 1}
                    </span>
                    {step}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="text-xs text-brand-700/70">© {year} Document AI</div>
        </div>
      </div>

      {/* Right: form */}
      <div className="flex w-full flex-col justify-center px-6 py-10 sm:px-10 lg:w-1/2">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="mx-auto w-full max-w-md"
        >
          {/* Mobile brand */}
          <div className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
              <FileText size={17} aria-hidden />
            </span>
            <span className="font-display text-base font-semibold text-slate-900">Document AI</span>
          </div>

          <div className="rounded-2xl bg-white p-6 shadow-soft ring-1 ring-brand-100 sm:p-8">
            <div className="mb-6 text-center">
              <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900">
                {c.title}
              </h1>
              <p className="mt-1.5 text-sm text-slate-500">{c.subtitle}</p>
            </div>

            {error && (
              <div className="mb-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden />
                <span>{error}</span>
              </div>
            )}
            {info && (
              <div className="mb-4 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                <CheckCircle2 size={16} className="mt-0.5 shrink-0" aria-hidden />
                <span>{info}</span>
              </div>
            )}

            {/* Social. Google always personalizes its own rendered button to
                "Sign in as <name>" once you're logged into Google, and there's no
                option to disable that. So we show our own consistent button and
                layer Google's real (invisible) button on top to capture the click
                and return a secure ID token — the backend/auth flow is unchanged. */}
            {(mode === "login" || mode === "register") && (
              <>
                <div className="relative h-10 w-full">
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center gap-2.5 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 shadow-sm">
                    <span className="text-base font-bold text-brand-600">G</span>
                    {mode === "register" ? "Sign up with Google" : "Sign in with Google"}
                  </div>
                  <div className="absolute inset-0 overflow-hidden opacity-0" aria-hidden={false}>
                    <GoogleLogin
                      onSuccess={(cred) => void onGoogle(cred.credential)}
                      onError={() =>
                        setError(
                          "Google sign-in failed. If you're the developer, authorize this origin in Google Cloud, or use email/password below."
                        )
                      }
                      type="standard"
                      theme="outline"
                      size="large"
                      width="400"
                    />
                  </div>
                </div>
                <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
                  <span className="h-px flex-1 bg-slate-200" />
                  Or
                  <span className="h-px flex-1 bg-slate-200" />
                </div>
              </>
            )}

            <form onSubmit={submit} className="space-y-4" autoComplete="off">
              {mode === "register" && (
                <div className="grid grid-cols-2 gap-3">
                  <Labeled label="First Name">
                    <input
                      className={inputCls}
                      type="text"
                      placeholder="eg. John"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      autoComplete="off"
                    />
                  </Labeled>
                  <Labeled label="Last Name">
                    <input
                      className={inputCls}
                      type="text"
                      placeholder="eg. Francisco"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      autoComplete="off"
                    />
                  </Labeled>
                </div>
              )}

              {(mode === "login" || mode === "register" || mode === "forgot") && (
                <Labeled label="Email">
                  <input
                    className={inputCls}
                    type="email"
                    placeholder="eg. johndoe@gmail.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="off"
                    required
                  />
                </Labeled>
              )}

              {(mode === "login" || mode === "register" || mode === "reset") && (
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-700">
                      {mode === "reset" ? "New Password" : "Password"}
                    </span>
                    {mode === "login" && (
                      <button
                        type="button"
                        onClick={() => switchMode("forgot")}
                        className="text-xs font-medium text-brand-600 hover:text-brand-700"
                      >
                        Forgot password?
                      </button>
                    )}
                  </div>
                  <div className="relative">
                    <input
                      className={cn(inputCls, "pr-10")}
                      type={showPw ? "text" : "password"}
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      autoComplete="new-password"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600"
                      aria-label={showPw ? "Hide password" : "Show password"}
                    >
                      {showPw ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                    </button>
                  </div>
                  {(mode === "register" || mode === "reset") && (
                    <p className="mt-1.5 text-xs text-slate-400">Must be at least 8 characters.</p>
                  )}
                </div>
              )}

              {mode === "reset" && (
                <Labeled label="Confirm Password">
                  <div className="relative">
                    <input
                      className={cn(inputCls, "pr-10")}
                      type={showPw2 ? "text" : "password"}
                      placeholder="Re-enter your password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      autoComplete="new-password"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw2((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600"
                      aria-label={showPw2 ? "Hide password" : "Show password"}
                    >
                      {showPw2 ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
                    </button>
                  </div>
                </Labeled>
              )}

              <button
                type="submit"
                disabled={busy}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-brand-700 disabled:opacity-60"
              >
                {busy && <Loader2 size={16} className="animate-spin" aria-hidden />}
                {c.cta}
              </button>
            </form>

            {/* Footer link */}
            <div className="mt-6 text-center text-sm text-slate-500">
              {mode === "login" && (
                <p>
                  Don't have an account?{" "}
                  <button
                    onClick={() => switchMode("register")}
                    className="font-semibold text-brand-700 hover:text-brand-800"
                  >
                    Sign up
                  </button>
                </p>
              )}
              {mode === "register" && (
                <p>
                  Already have an account?{" "}
                  <button
                    onClick={() => switchMode("login")}
                    className="font-semibold text-brand-700 hover:text-brand-800"
                  >
                    Log in
                  </button>
                </p>
              )}
              {(mode === "forgot" || mode === "reset") && (
                <button
                  onClick={() => switchMode("login")}
                  className="inline-flex items-center gap-1 font-medium text-brand-600 hover:text-brand-700"
                >
                  <ArrowLeft size={14} aria-hidden /> Back to sign in
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
