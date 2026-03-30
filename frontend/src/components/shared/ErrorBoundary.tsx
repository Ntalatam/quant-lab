"use client";

import { AlertTriangle } from "lucide-react";

export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 p-4 rounded bg-accent-red/10 border border-accent-red/20 text-accent-red">
      <AlertTriangle size={18} />
      <p className="text-sm">{message}</p>
    </div>
  );
}
