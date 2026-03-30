"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Global keyboard shortcuts:
 *   N  → New Backtest (/backtest)
 *   R  → Results (/results)
 *   D  → Dashboard (/)
 *   C  → Compare (/compare)
 *   ?  → Toggle shortcuts help overlay (handled in component)
 */
export function useKeyboardShortcuts() {
  const router = useRouter();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore when typing in inputs, textareas, etc.
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.tagName === "SELECT" ||
        target.isContentEditable
      ) {
        return;
      }

      // Ignore modified keypresses (Ctrl, Cmd, Alt)
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      switch (e.key) {
        case "n":
        case "N":
          e.preventDefault();
          router.push("/backtest");
          break;
        case "r":
        case "R":
          e.preventDefault();
          router.push("/results");
          break;
        case "d":
        case "D":
          e.preventDefault();
          router.push("/");
          break;
        case "c":
        case "C":
          e.preventDefault();
          router.push("/compare");
          break;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [router]);
}
