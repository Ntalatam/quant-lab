"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { Sidebar } from "@/components/layout/Sidebar";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { useSession } from "@/components/auth/SessionProvider";

const PUBLIC_PATHS = new Set(["/login", "/register", "/healthz"]);

function isPublicPath(pathname: string | null): boolean {
  if (!pathname) {
    return false;
  }
  return PUBLIC_PATHS.has(pathname);
}

export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useSession();
  const publicPath = isPublicPath(pathname);

  useEffect(() => {
    if (status === "authenticated" && publicPath) {
      const next =
        typeof window !== "undefined"
          ? new URLSearchParams(window.location.search).get("next") || "/"
          : "/";
      router.replace(next);
    }
  }, [publicPath, router, status]);

  useEffect(() => {
    if (publicPath || status !== "unauthenticated") {
      return;
    }
    const next = pathname ? `?next=${encodeURIComponent(pathname)}` : "";
    router.replace(`/login${next}`);
  }, [pathname, publicPath, router, status]);

  if (publicPath) {
    if (status === "authenticated") {
      return <PageLoading />;
    }

    return (
      <main className="relative flex min-h-screen w-full items-center justify-center overflow-hidden bg-[var(--color-bg-primary)] px-4 py-8">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "radial-gradient(circle at top left, rgba(68,136,255,0.16), transparent 32%), radial-gradient(circle at bottom right, rgba(40,221,176,0.12), transparent 30%)",
          }}
        />
        <div className="relative z-10 w-full max-w-5xl">{children}</div>
      </main>
    );
  }

  if (status !== "authenticated") {
    return (
      <main className="flex min-h-screen w-full items-center justify-center bg-[var(--color-bg-primary)]">
        <PageLoading />
      </main>
    );
  }

  return (
    <>
      <Sidebar />
      <main className="relative flex-1 min-h-screen overflow-x-hidden lg:ml-64">
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            background:
              "linear-gradient(180deg, rgba(255,255,255,0.018) 0%, transparent 18%)",
          }}
        />
        <div className="relative mx-auto min-h-screen w-full max-w-[1660px] px-4 pb-8 pt-16 lg:px-8 lg:pb-12 lg:pt-8">
          {children}
        </div>
      </main>
    </>
  );
}
