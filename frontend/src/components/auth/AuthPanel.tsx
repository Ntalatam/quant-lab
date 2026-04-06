"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowRight, LockKeyhole, Mail, User2 } from "lucide-react";

import { useSession } from "@/components/auth/SessionProvider";

export function AuthPanel({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const { login, register } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nextPath = useMemo(() => {
    if (typeof window === "undefined") {
      return "/";
    }
    return new URLSearchParams(window.location.search).get("next") || "/";
  }, []);
  const isRegister = mode === "register";

  const title = isRegister
    ? "Create your research workspace"
    : "Sign in to QuantLab";
  const description = isRegister
    ? "Set up your personal workspace so backtests, strategy drafts, and paper sessions belong to you from day one."
    : "Pick up exactly where you left off across saved tear sheets, strategy experiments, and paper-trading sessions.";

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isRegister) {
        await register({
          email,
          password,
          display_name: displayName.trim() || undefined,
        });
      } else {
        await login({ email, password });
      }
      router.replace(nextPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr]">
      <section className="panel-hero panel-grid overflow-hidden px-6 py-8 lg:px-8 lg:py-10">
        <div className="page-kicker mb-5">Workspace Security</div>
        <h1 className="display-title text-4xl text-text-primary lg:text-5xl">
          Research with a real
          <span className="text-accent-green"> ownership layer. </span>
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-text-secondary lg:text-[15px]">
          QuantLab now keeps your saved runs, custom strategies, and paper
          sessions inside a personal workspace, so the product is ready for the
          next phase of multi-user research workflows.
        </p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            "Short-lived access tokens",
            "Rotating refresh sessions",
            "Workspace-scoped research artifacts",
          ].map((label) => (
            <div
              key={label}
              className="rounded-3xl border border-border/60 bg-bg-card/65 px-4 py-3 text-xs text-text-secondary"
            >
              {label}
            </div>
          ))}
        </div>
      </section>

      <section className="panel-soft p-6 lg:p-8">
        <div className="mb-6">
          <p className="section-label mb-3">
            {isRegister ? "Register" : "Login"}
          </p>
          <h2 className="text-2xl font-semibold tracking-tight text-text-primary">
            {title}
          </h2>
          <p className="mt-2 text-sm leading-6 text-text-secondary">
            {description}
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {isRegister ? (
            <label className="block">
              <span className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-text-muted">
                <User2 size={12} />
                Display Name
              </span>
              <input
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
                placeholder="Alex Quant"
                className="w-full rounded-3xl border border-border/70 bg-bg-card px-4 py-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue"
              />
            </label>
          ) : null}

          <label className="block">
            <span className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-text-muted">
              <Mail size={12} />
              Email
            </span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
              className="w-full rounded-3xl border border-border/70 bg-bg-card px-4 py-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue"
            />
          </label>

          <label className="block">
            <span className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-text-muted">
              <LockKeyhole size={12} />
              Password
            </span>
            <input
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={
                isRegister ? "Minimum 8 characters" : "Enter password"
              }
              required
              className="w-full rounded-3xl border border-border/70 bg-bg-card px-4 py-3 text-sm text-text-primary outline-none transition-colors focus:border-accent-blue"
            />
          </label>

          {error ? (
            <div
              className="rounded-3xl px-4 py-3 text-sm text-accent-red"
              style={{
                background: "rgba(255,71,87,0.08)",
                border: "1px solid rgba(255,71,87,0.24)",
              }}
            >
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="action-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
          >
            <ArrowRight size={14} />
            {isSubmitting
              ? isRegister
                ? "Creating workspace…"
                : "Signing in…"
              : isRegister
                ? "Create account"
                : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-sm text-text-secondary">
          {isRegister ? "Already have an account?" : "Need an account?"}{" "}
          <Link
            href={
              isRegister
                ? `/login?next=${encodeURIComponent(nextPath)}`
                : `/register?next=${encodeURIComponent(nextPath)}`
            }
            className="font-medium text-accent-green transition-opacity hover:opacity-80"
          >
            {isRegister ? "Sign in" : "Create one"}
          </Link>
        </p>
      </section>
    </div>
  );
}
