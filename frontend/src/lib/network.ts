const FALLBACK_API_BASE = "http://localhost:8000/api";

function ensureLeadingSlash(value: string): string {
  return value.startsWith("/") ? value : `/${value}`;
}

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

export function getApiBaseUrl(
  rawBase: string | undefined = process.env.NEXT_PUBLIC_API_URL,
): string {
  return trimTrailingSlash(rawBase?.trim() || FALLBACK_API_BASE);
}

export function buildApiUrl(
  path: string,
  apiBase: string = getApiBaseUrl(),
): string {
  return `${apiBase}${ensureLeadingSlash(path)}`;
}

export function buildWebSocketUrl(
  path: string,
  apiBase: string = getApiBaseUrl(),
  currentOrigin?: string,
): string {
  const normalizedPath = ensureLeadingSlash(path);

  if (apiBase.startsWith("http://") || apiBase.startsWith("https://")) {
    const url = new URL(normalizedPath, apiBase);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return url.toString();
  }

  const origin =
    currentOrigin ||
    (typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost:3000");
  const url = new URL(normalizedPath, origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
