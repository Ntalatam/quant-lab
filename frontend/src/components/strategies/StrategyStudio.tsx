"use client";

import dynamic from "next/dynamic";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Code2,
  Loader2,
  Plus,
  Save,
  ScrollText,
  Trash2,
} from "lucide-react";

import {
  useCreateCustomStrategy,
  useCustomStrategies,
  useDeleteCustomStrategy,
  useStrategyEditorSpec,
  useUpdateCustomStrategy,
} from "@/hooks/useCustomStrategies";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/formatters";
import type { StrategyValidationResult } from "@/lib/types";

const CodeMirror = dynamic(() => import("@uiw/react-codemirror"), {
  ssr: false,
});

const NEW_DRAFT_KEY = "__new__";

function encodeBacktestPreset(
  strategyId: string,
  defaults: Record<string, number | string | boolean>,
) {
  return encodeURIComponent(
    btoa(
      JSON.stringify({
        strategy_id: strategyId,
        params: defaults,
      }),
    ),
  );
}

function ValidationTone({
  validation,
  validating,
}: {
  validation: StrategyValidationResult | null;
  validating: boolean;
}) {
  if (validating) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-accent-blue">
        <Loader2 size={12} className="animate-spin" />
        Validating…
      </div>
    );
  }

  if (validation?.valid) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-accent-green">
        <CheckCircle2 size={12} />
        Ready to save
      </div>
    );
  }

  if (validation && !validation.valid) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-accent-red">
        <AlertTriangle size={12} />
        Needs fixes
      </div>
    );
  }

  return <div className="text-[11px] text-text-muted">Waiting for code…</div>;
}

export function StrategyStudio() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedStrategyId = searchParams.get("strategyId");

  const {
    data: editorSpec,
    isLoading: specLoading,
    error: specError,
  } = useStrategyEditorSpec();
  const {
    data: customStrategies,
    isLoading: customLoading,
    error: customError,
  } = useCustomStrategies();
  const createMutation = useCreateCustomStrategy();
  const updateMutation = useUpdateCustomStrategy();
  const deleteMutation = useDeleteCustomStrategy();

  const [selectedKey, setSelectedKey] = useState<string>(
    requestedStrategyId ?? NEW_DRAFT_KEY,
  );
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [savedSnapshots, setSavedSnapshots] = useState<Record<string, string>>(
    {},
  );
  const [validation, setValidation] = useState<StrategyValidationResult | null>(
    null,
  );
  const [validating, setValidating] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [statusTone, setStatusTone] = useState<"success" | "error" | "info">(
    "info",
  );

  const selectedStrategy =
    customStrategies?.find((strategy) => strategy.id === selectedKey) ?? null;
  const draftCode = drafts[selectedKey] ?? "";
  const deferredCode = useDeferredValue(draftCode);
  const isExistingStrategy = selectedKey !== NEW_DRAFT_KEY;
  const baselineCode = savedSnapshots[selectedKey] ?? "";
  const isDirty = !!draftCode && draftCode !== baselineCode;
  const canUseInBacktest =
    isExistingStrategy &&
    !!validation?.valid &&
    !!validation.extracted?.defaults &&
    !!selectedStrategy;

  useEffect(() => {
    if (!editorSpec?.template) return;
    setDrafts((current) =>
      current[NEW_DRAFT_KEY]
        ? current
        : { ...current, [NEW_DRAFT_KEY]: editorSpec.template },
    );
    setSavedSnapshots((current) =>
      current[NEW_DRAFT_KEY]
        ? current
        : { ...current, [NEW_DRAFT_KEY]: editorSpec.template },
    );
  }, [editorSpec?.template]);

  useEffect(() => {
    if (!requestedStrategyId) {
      setSelectedKey((current) => (current ? current : NEW_DRAFT_KEY));
      return;
    }
    setSelectedKey(requestedStrategyId);
  }, [requestedStrategyId]);

  useEffect(() => {
    if (!selectedStrategy) return;
    if (drafts[selectedStrategy.id]) return;

    let cancelled = false;
    const load = async () => {
      try {
        const detail = await api.getCustomStrategy(selectedStrategy.id);
        if (cancelled) return;
        setDrafts((current) => ({ ...current, [detail.id]: detail.code }));
        setSavedSnapshots((current) => ({
          ...current,
          [detail.id]: detail.code,
        }));
      } catch (error) {
        if (!cancelled) {
          setStatusTone("error");
          setStatusMessage(
            error instanceof Error
              ? error.message
              : "Could not load custom strategy",
          );
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [drafts, selectedStrategy]);

  useEffect(() => {
    if (!deferredCode.trim()) {
      setValidation(null);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setValidating(true);
      try {
        const response = await api.validateCustomStrategy(deferredCode);
        if (cancelled) return;
        startTransition(() => {
          setValidation(response);
        });
      } catch (error) {
        if (cancelled) return;
        startTransition(() => {
          setValidation({
            valid: false,
            errors: [
              error instanceof Error ? error.message : "Validation failed",
            ],
            warnings: [],
            extracted: null,
            preview: null,
          });
        });
      } finally {
        if (!cancelled) {
          setValidating(false);
        }
      }
    }, 450);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [deferredCode]);

  const preview = validation?.preview;
  const extractedDefaults = validation?.extracted?.defaults ?? {};
  const extractedParams = validation?.extracted?.params ?? [];
  const activeName =
    preview?.name ?? selectedStrategy?.name ?? "Untitled Strategy";

  const handleSelectStrategy = (strategyId: string) => {
    setSelectedKey(strategyId);
    router.replace(`/strategies/custom?strategyId=${strategyId}`);
  };

  const handleNewDraft = () => {
    setSelectedKey(NEW_DRAFT_KEY);
    setStatusTone("info");
    setStatusMessage("Started a fresh draft from the editor template.");
    router.replace("/strategies/custom");
  };

  const handleSave = async () => {
    if (!validation?.valid) {
      setStatusTone("error");
      setStatusMessage("Fix the validation errors before saving.");
      return;
    }

    try {
      const response = isExistingStrategy
        ? await updateMutation.mutateAsync({ id: selectedKey, code: draftCode })
        : await createMutation.mutateAsync(draftCode);

      setDrafts((current) => ({
        ...current,
        [response.id]: response.code,
        [NEW_DRAFT_KEY]: editorSpec?.template ?? current[NEW_DRAFT_KEY] ?? "",
      }));
      setSavedSnapshots((current) => ({
        ...current,
        [response.id]: response.code,
        [NEW_DRAFT_KEY]: editorSpec?.template ?? current[NEW_DRAFT_KEY] ?? "",
      }));
      setSelectedKey(response.id);
      setStatusTone("success");
      setStatusMessage(
        isExistingStrategy
          ? `Updated ${response.name}.`
          : `Saved ${response.name} and added it to your strategy library.`,
      );
      router.replace(`/strategies/custom?strategyId=${response.id}`);
    } catch (error) {
      setStatusTone("error");
      setStatusMessage(
        error instanceof Error ? error.message : "Could not save strategy",
      );
    }
  };

  const handleDelete = async () => {
    if (!isExistingStrategy) return;
    try {
      await deleteMutation.mutateAsync(selectedKey);
      setDrafts((current) => {
        const next = { ...current };
        delete next[selectedKey];
        return next;
      });
      setSavedSnapshots((current) => {
        const next = { ...current };
        delete next[selectedKey];
        return next;
      });
      setSelectedKey(NEW_DRAFT_KEY);
      setStatusTone("success");
      setStatusMessage("Deleted the custom strategy.");
      router.replace("/strategies/custom");
    } catch (error) {
      setStatusTone("error");
      setStatusMessage(
        error instanceof Error ? error.message : "Could not delete strategy",
      );
    }
  };

  const handleUseInBacktest = () => {
    if (!canUseInBacktest || !selectedStrategy) return;
    router.push(
      `/backtest?config=${encodeBacktestPreset(selectedStrategy.id, extractedDefaults)}`,
    );
  };

  const helperGroups = useMemo(() => {
    if (!editorSpec?.helpers) return [];
    return [
      {
        label: "Data & Signals",
        items: editorSpec.helpers.slice(0, 4),
      },
      {
        label: "Indicators",
        items: editorSpec.helpers.slice(4, 14),
      },
      {
        label: "Ranking & Utils",
        items: editorSpec.helpers.slice(14),
      },
    ];
  }, [editorSpec?.helpers]);

  if (specLoading || customLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Loader2 size={15} className="animate-spin text-accent-blue" />
        Loading strategy studio…
      </div>
    );
  }

  if (specError || customError || !editorSpec) {
    return (
      <div
        className="rounded-md p-4 text-sm"
        style={{
          background: "rgba(255,71,87,0.08)",
          border: "1px solid rgba(255,71,87,0.22)",
          color: "var(--color-accent-red)",
        }}
      >
        {specError?.message ??
          customError?.message ??
          "Could not load the strategy studio."}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-text-primary">
            Strategy Studio
          </h1>
          <p className="mt-0.5 max-w-3xl text-xs leading-relaxed text-text-muted">
            Write custom Python strategies with syntax highlighting, safe helper
            functions, extracted parameter forms, and one-click handoff into
            backtests.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleNewDraft}
            className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs"
            style={{
              background: "rgba(68,136,255,0.1)",
              border: "1px solid rgba(68,136,255,0.2)",
              color: "var(--color-accent-blue)",
            }}
          >
            <Plus size={12} />
            New Draft
          </button>
          <button
            onClick={handleSave}
            disabled={
              !draftCode.trim() ||
              validating ||
              createMutation.isPending ||
              updateMutation.isPending
            }
            className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs disabled:opacity-40"
            style={{
              background: "rgba(0,212,170,0.1)",
              border: "1px solid rgba(0,212,170,0.24)",
              color: "var(--color-accent-green)",
            }}
          >
            {createMutation.isPending || updateMutation.isPending ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Save size={12} />
            )}
            {isExistingStrategy ? "Save Changes" : "Save Strategy"}
          </button>
          <button
            onClick={handleUseInBacktest}
            disabled={!canUseInBacktest}
            className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs disabled:opacity-40"
            style={{
              background: "rgba(255,187,51,0.1)",
              border: "1px solid rgba(255,187,51,0.22)",
              color: "var(--color-accent-yellow)",
            }}
          >
            <ArrowRight size={12} />
            Use in Backtest
          </button>
          {isExistingStrategy && (
            <button
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs disabled:opacity-40"
              style={{
                background: "rgba(255,71,87,0.08)",
                border: "1px solid rgba(255,71,87,0.22)",
                color: "var(--color-accent-red)",
              }}
            >
              {deleteMutation.isPending ? (
                <Loader2 size={12} className="animate-spin" />
              ) : (
                <Trash2 size={12} />
              )}
              Delete
            </button>
          )}
        </div>
      </div>

      {statusMessage && (
        <div
          className="rounded-md px-4 py-3 text-xs"
          style={{
            background:
              statusTone === "success"
                ? "rgba(0,212,170,0.08)"
                : statusTone === "error"
                  ? "rgba(255,71,87,0.08)"
                  : "rgba(68,136,255,0.08)",
            border:
              statusTone === "success"
                ? "1px solid rgba(0,212,170,0.22)"
                : statusTone === "error"
                  ? "1px solid rgba(255,71,87,0.22)"
                  : "1px solid rgba(68,136,255,0.22)",
            color:
              statusTone === "success"
                ? "var(--color-accent-green)"
                : statusTone === "error"
                  ? "var(--color-accent-red)"
                  : "var(--color-accent-blue)",
          }}
        >
          {statusMessage}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)_22rem]">
        <div
          className="rounded-md p-4"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div className="mb-3 flex items-center gap-2">
            <ScrollText size={13} className="text-accent-blue" />
            <div>
              <p className="text-sm font-semibold text-text-primary">
                Saved Strategies
              </p>
              <p className="text-[10px] text-text-muted">
                Persisted custom strategies appear here and in the global
                library.
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <button
              onClick={handleNewDraft}
              className={`w-full rounded-md px-3 py-2 text-left text-xs transition-colors ${
                selectedKey === NEW_DRAFT_KEY
                  ? "text-text-primary"
                  : "text-text-secondary"
              }`}
              style={{
                background:
                  selectedKey === NEW_DRAFT_KEY
                    ? "rgba(68,136,255,0.08)"
                    : "var(--color-bg-primary)",
                border:
                  selectedKey === NEW_DRAFT_KEY
                    ? "1px solid rgba(68,136,255,0.22)"
                    : "1px solid var(--color-border)",
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">Unsaved Draft</span>
                {selectedKey === NEW_DRAFT_KEY && isDirty && (
                  <span className="text-[10px] text-accent-yellow">dirty</span>
                )}
              </div>
              <p className="mt-1 text-[10px] text-text-muted">
                Start from the safe template and save when validation is green.
              </p>
            </button>

            {customStrategies?.map((strategy) => (
              <button
                key={strategy.id}
                onClick={() => handleSelectStrategy(strategy.id)}
                className={`w-full rounded-md px-3 py-2 text-left text-xs transition-colors ${
                  selectedKey === strategy.id
                    ? "text-text-primary"
                    : "text-text-secondary"
                }`}
                style={{
                  background:
                    selectedKey === strategy.id
                      ? "rgba(0,212,170,0.08)"
                      : "var(--color-bg-primary)",
                  border:
                    selectedKey === strategy.id
                      ? "1px solid rgba(0,212,170,0.22)"
                      : "1px solid var(--color-border)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{strategy.name}</span>
                  <span className="text-[10px] uppercase tracking-[0.16em] text-text-muted">
                    {strategy.signal_mode === "long_short" ? "L/S" : "LONG"}
                  </span>
                </div>
                <p className="mt-1 line-clamp-2 text-[10px] text-text-muted">
                  {strategy.description}
                </p>
                <p className="mt-2 text-[10px] text-text-muted">
                  Updated {formatDate(strategy.updated_at)}
                </p>
              </button>
            ))}
          </div>
        </div>

        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow:
              "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
          }}
        >
          <div
            className="flex flex-col gap-3 px-5 py-3 lg:flex-row lg:items-center lg:justify-between"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <div className="flex items-center gap-2">
              <Code2 size={13} className="text-accent-purple" />
              <div>
                <p className="text-sm font-semibold text-text-primary">
                  {activeName}
                </p>
                <p className="text-[10px] text-text-muted">
                  {preview?.description ??
                    selectedStrategy?.description ??
                    "Edit the strategy source, then let the backend extract the UI schema and validate the runtime."}
                </p>
              </div>
            </div>
            <ValidationTone validation={validation} validating={validating} />
          </div>

          <div className="min-h-[640px]">
            <CodeMirror
              value={draftCode}
              height="640px"
              theme={oneDark}
              extensions={[python()]}
              basicSetup={{
                lineNumbers: true,
                foldGutter: true,
                highlightActiveLine: true,
                autocompletion: true,
              }}
              onChange={(value) =>
                setDrafts((current) => ({ ...current, [selectedKey]: value }))
              }
            />
          </div>
        </div>

        <div className="space-y-5">
          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
            }}
          >
            <p className="text-sm font-semibold text-text-primary">
              Extracted Parameters
            </p>
            <p className="mt-1 text-[10px] text-text-muted">
              Saved strategies automatically show up in the backtest and
              paper-trading forms.
            </p>

            {validation?.errors?.length ? (
              <div className="mt-3 space-y-2">
                {validation.errors.map((error) => (
                  <div
                    key={error}
                    className="rounded p-2 text-[11px]"
                    style={{
                      background: "rgba(255,71,87,0.08)",
                      border: "1px solid rgba(255,71,87,0.18)",
                      color: "var(--color-accent-red)",
                    }}
                  >
                    {error}
                  </div>
                ))}
              </div>
            ) : extractedParams.length > 0 ? (
              <div className="mt-3 space-y-2">
                {extractedParams.map((param) => (
                  <div
                    key={param.name}
                    className="rounded p-3"
                    style={{
                      background: "var(--color-bg-primary)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium text-text-primary">
                        {param.label}
                      </p>
                      <span className="text-[10px] uppercase tracking-[0.16em] text-text-muted">
                        {param.type}
                      </span>
                    </div>
                    <p className="mt-1 text-[10px] text-text-muted">
                      Default: {String(param.default)}
                    </p>
                    <p className="mt-1 text-[10px] leading-relaxed text-text-muted">
                      {param.description}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-xs text-text-muted">
                The extracted parameter schema will appear here after the draft
                validates.
              </p>
            )}

            {validation?.warnings?.length ? (
              <div className="mt-3 space-y-2">
                {validation.warnings.map((warning) => (
                  <div
                    key={warning}
                    className="rounded p-2 text-[11px]"
                    style={{
                      background: "rgba(255,187,51,0.08)",
                      border: "1px solid rgba(255,187,51,0.18)",
                      color: "var(--color-accent-yellow)",
                    }}
                  >
                    {warning}
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
            }}
          >
            <p className="text-sm font-semibold text-text-primary">
              Editor Rules
            </p>
            <div className="mt-3 space-y-2 text-[11px] text-text-muted">
              {editorSpec.rules.map((rule) => (
                <div
                  key={rule}
                  className="rounded p-2"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  {rule}
                </div>
              ))}
            </div>
          </div>

          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
            }}
          >
            <p className="text-sm font-semibold text-text-primary">
              Helper Catalog
            </p>
            <div className="mt-3 space-y-4">
              {helperGroups.map((group) => (
                <div key={group.label}>
                  <p className="section-label mb-2">{group.label}</p>
                  <div className="space-y-2">
                    {group.items.map((helper) => (
                      <div
                        key={helper.name}
                        className="rounded p-2"
                        style={{
                          background: "var(--color-bg-primary)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        <p className="font-mono text-[11px] text-text-primary">
                          {helper.signature}
                        </p>
                        <p className="mt-1 text-[10px] leading-relaxed text-text-muted">
                          {helper.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
