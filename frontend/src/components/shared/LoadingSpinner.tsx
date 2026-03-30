"use client";

export function LoadingSpinner({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      className="animate-spin text-accent-blue"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        className="opacity-15"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function PageLoading() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <LoadingSpinner size={28} />
      <p className="text-[11px] text-text-muted tracking-wider uppercase animate-pulse">
        Loading…
      </p>
    </div>
  );
}
