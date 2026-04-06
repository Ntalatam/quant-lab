"use client";

import {
  createContext,
  startTransition,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { AUTH_TOKEN_STORAGE_KEY, api } from "@/lib/api";
import type { AuthSession, AuthUser, AuthWorkspace } from "@/lib/types";

type SessionStatus = "loading" | "authenticated" | "unauthenticated";

interface SessionContextValue {
  status: SessionStatus;
  accessToken: string | null;
  user: AuthUser | null;
  workspace: AuthWorkspace | null;
  login: (payload: { email: string; password: string }) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    display_name?: string | null;
  }) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function persistAccessToken(token: string | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
}

function readStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
}

function toSessionState(session: {
  accessToken: string | null;
  user: AuthUser;
  workspace: AuthWorkspace;
}) {
  return {
    status: "authenticated" as const,
    accessToken: session.accessToken,
    user: session.user,
    workspace: session.workspace,
  };
}

function toSessionStateFromAuth(session: AuthSession) {
  return toSessionState({
    accessToken: session.access_token,
    user: session.user,
    workspace: session.workspace,
  });
}

export function SessionProvider({
  children,
  bootstrap = true,
  initialSession = null,
}: {
  children: ReactNode;
  bootstrap?: boolean;
  initialSession?: {
    accessToken: string | null;
    user: AuthUser;
    workspace: AuthWorkspace;
  } | null;
}) {
  const [state, setState] = useState(() =>
    initialSession
      ? toSessionState(initialSession)
      : {
          status: bootstrap
            ? ("loading" as const)
            : ("unauthenticated" as const),
          accessToken: null,
          user: null,
          workspace: null,
        },
  );

  useEffect(() => {
    if (!bootstrap || initialSession) {
      return;
    }

    let cancelled = false;

    const bootstrapSession = async () => {
      const storedToken = readStoredAccessToken();
      api.setAccessToken(storedToken);

      try {
        const payload = await api.getCurrentSession();
        if (cancelled) {
          return;
        }
        const nextToken = api.getAccessToken() ?? storedToken;
        persistAccessToken(nextToken);
        startTransition(() => {
          setState(
            toSessionState({
              accessToken: nextToken,
              user: payload.user,
              workspace: payload.workspace,
            }),
          );
        });
      } catch {
        if (cancelled) {
          return;
        }
        api.setAccessToken(null);
        persistAccessToken(null);
        startTransition(() => {
          setState({
            status: "unauthenticated",
            accessToken: null,
            user: null,
            workspace: null,
          });
        });
      }
    };

    void bootstrapSession();

    return () => {
      cancelled = true;
    };
  }, [bootstrap, initialSession]);

  const value = useMemo<SessionContextValue>(
    () => ({
      status: state.status,
      accessToken: state.accessToken,
      user: state.user,
      workspace: state.workspace,
      login: async (payload) => {
        const session = await api.login(payload);
        api.setAccessToken(session.access_token);
        persistAccessToken(session.access_token);
        startTransition(() => {
          setState(toSessionStateFromAuth(session));
        });
      },
      register: async (payload) => {
        const session = await api.register(payload);
        api.setAccessToken(session.access_token);
        persistAccessToken(session.access_token);
        startTransition(() => {
          setState(toSessionStateFromAuth(session));
        });
      },
      logout: async () => {
        try {
          await api.logout();
        } finally {
          api.setAccessToken(null);
          persistAccessToken(null);
          startTransition(() => {
            setState({
              status: "unauthenticated",
              accessToken: null,
              user: null,
              workspace: null,
            });
          });
        }
      },
      refresh: async () => {
        const session = await api.refreshSession();
        api.setAccessToken(session.access_token);
        persistAccessToken(session.access_token);
        startTransition(() => {
          setState(toSessionStateFromAuth(session));
        });
      },
    }),
    [state],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useSession() {
  const value = useContext(SessionContext);
  if (!value) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return value;
}
