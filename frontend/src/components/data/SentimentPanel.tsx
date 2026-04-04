"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { NewsSentimentResult } from "@/lib/types";

function scoreTone(score: number) {
  if (score >= 0.2) return "bullish";
  if (score <= -0.2) return "bearish";
  return "neutral";
}

export function SentimentPanel({
  sentiment,
  isLoading,
}: {
  sentiment: NewsSentimentResult | undefined;
  isLoading: boolean;
}) {
  const tone = scoreTone(sentiment?.average_score ?? 0);
  const toneColor =
    tone === "bullish"
      ? "var(--color-accent-green)"
      : tone === "bearish"
        ? "var(--color-accent-red)"
        : "var(--color-accent-blue)";

  return (
    <div className="card p-5 space-y-4 h-full">
      <div>
        <h2 className="text-sm font-semibold text-text-primary">
          News Sentiment
        </h2>
        <p className="text-xs text-text-muted mt-1">
          A finance-aware lexical model scores ticker-linked news headlines and
          descriptions over the recent window.
        </p>
      </div>

      {isLoading ? (
        <div className="py-10 text-sm text-text-muted text-center">
          Scoring recent news…
        </div>
      ) : sentiment ? (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <MetricCard
              label="Average Score"
              value={sentiment.average_score.toFixed(2)}
              accent={toneColor}
            />
            <MetricCard
              label="Signal"
              value={sentiment.signal}
              accent={toneColor}
            />
            <MetricCard
              label="Articles"
              value={String(sentiment.article_count)}
            />
            <MetricCard
              label="Bull / Bear"
              value={`${sentiment.bullish_articles}/${sentiment.bearish_articles}`}
            />
          </div>

          <div className="h-[220px]">
            {sentiment.rolling_series.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sentiment.rolling_series}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
                  <XAxis dataKey="date" minTickGap={28} />
                  <YAxis domain={[-1, 1]} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--color-bg-card)",
                      border: "1px solid var(--color-border)",
                      borderRadius: 6,
                    }}
                  />
                  <ReferenceLine
                    y={0}
                    stroke="var(--color-text-muted)"
                    strokeDasharray="4 4"
                  />
                  <Line
                    type="monotone"
                    dataKey="average_score"
                    stroke={toneColor}
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-text-muted">
                No recent headlines in the selected lookback window.
              </div>
            )}
          </div>

          <div className="space-y-2">
            {sentiment.articles.map((article) => (
              <a
                key={article.id}
                href={article.url ?? undefined}
                target="_blank"
                rel="noreferrer"
                className="block rounded px-3 py-2.5 transition-colors hover:bg-bg-hover"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-text-primary">
                      {article.title}
                    </p>
                    <p className="text-[11px] text-text-muted mt-0.5">
                      {article.publisher} • {article.published_at.slice(0, 10)}
                    </p>
                  </div>
                  <span
                    className="text-[11px] font-medium uppercase"
                    style={{
                      color:
                        article.sentiment_score >= 0
                          ? "var(--color-accent-green)"
                          : "var(--color-accent-red)",
                    }}
                  >
                    {article.sentiment_score >= 0 ? "+" : ""}
                    {article.sentiment_score.toFixed(2)}
                  </span>
                </div>
                {article.summary && (
                  <p className="text-[12px] text-text-secondary mt-2 line-clamp-2">
                    {article.summary}
                  </p>
                )}
              </a>
            ))}
          </div>
        </>
      ) : (
        <div className="py-10 text-sm text-text-muted text-center">
          Select a ticker to analyze recent sentiment.
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: string;
}) {
  return (
    <div
      className="rounded p-3"
      style={{
        background: "var(--color-bg-primary)",
        border: "1px solid var(--color-border)",
      }}
    >
      <p className="section-label">{label}</p>
      <p
        className="text-lg mt-2 font-semibold capitalize"
        style={{ color: accent ?? "var(--color-text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}
