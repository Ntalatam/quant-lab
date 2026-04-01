"use client";

import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import { FileText, Check, Loader2 } from "lucide-react";

interface NotesEditorProps {
  backtestId: string;
  initialNotes?: string;
}

export function NotesEditor({ backtestId, initialNotes = "" }: NotesEditorProps) {
  const [notes, setNotes] = useState(initialNotes);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);

  const save = useCallback(async () => {
    if (saving) return;
    setSaving(true);
    setSaveError(false);
    try {
      await api.updateNotes(backtestId, notes);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setSaveError(true);
      setTimeout(() => setSaveError(false), 4000);
    } finally {
      setSaving(false);
    }
  }, [backtestId, notes, saving]);

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
      }}
    >
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <FileText size={13} className="text-text-muted" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Research Notes</h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Annotate this run — hypothesis, observations, next steps
            </p>
          </div>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-all disabled:opacity-40"
          style={{
            background: saveError
              ? "rgba(255,68,102,0.15)"
              : saved
              ? "rgba(0,212,170,0.15)"
              : "rgba(68,136,255,0.1)",
            border: `1px solid ${saveError ? "rgba(255,68,102,0.3)" : saved ? "rgba(0,212,170,0.3)" : "rgba(68,136,255,0.2)"}`,
            color: saveError
              ? "var(--color-accent-red)"
              : saved
              ? "var(--color-accent-green)"
              : "var(--color-accent-blue)",
          }}
        >
          {saving ? (
            <Loader2 size={11} className="animate-spin" />
          ) : saved ? (
            <Check size={11} />
          ) : (
            <FileText size={11} />
          )}
          {saving ? "Saving…" : saveError ? "Save failed" : saved ? "Saved" : "Save"}
        </button>
      </div>
      <div className="p-4">
        <textarea
          value={notes}
          onChange={(e) => { setNotes(e.target.value); setSaved(false); }}
          onBlur={save}
          placeholder="e.g. Testing shorter lookback to reduce lag. 2022 drawdown driven by rate hikes — strategy held through it. Compare to momentum run #3a2f…"
          rows={4}
          maxLength={2000}
          className="w-full text-xs text-text-primary placeholder:text-text-muted resize-none focus:outline-none leading-relaxed"
          style={{
            background: "transparent",
            border: "none",
            fontFamily: "inherit",
          }}
        />
        <div className="flex justify-between items-center mt-1">
          <span className="text-[10px] text-text-muted">
            Auto-saves on blur · {notes.length}/2000
          </span>
        </div>
      </div>
    </div>
  );
}
