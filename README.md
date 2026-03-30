# QuantLab

A full-stack quantitative research platform for backtesting systematic trading strategies against real historical market data. Built to demonstrate production-quality financial engineering — not a Jupyter notebook wrapper.

---

## What Makes This Different

Most student backtest projects are thin pandas scripts that compute a moving average and plot a line. QuantLab differentiates by:

- **Event-driven engine** — processes one bar at a time, maintaining realistic portfolio state. No lookahead bias. No vectorized shortcuts.
- **Realistic market simulation** — models slippage, commissions, volume constraints, and position sizing. Markets are not frictionless.
- **Research-grade analytics** — 25+ metrics including Sharpe, Sortino, Calmar, CVaR, alpha, beta, rolling metrics, and a monthly returns heatmap.
- **Multi-strategy comparison** — run 4 different strategy families and compare them head-to-head with correlation analysis.
- **Live progress streaming** — WebSocket-based real-time progress updates: watch equity build bar-by-bar as the simulation runs.
- **Production engineering** — clean REST API, async database layer, persistent results, comprehensive test suite, CI/CD, Docker.

---

## Advanced Analysis Features

### Transaction Cost Breakdown
Every backtest shows the gap between actual strategy performance and frictionless execution:
- **Frictionless equity curve** — what you'd earn with zero slippage/commission, overlaid as a dashed blue line
- **Cost drag** — total commission + slippage expressed in bps and as a percentage of initial capital
- Separate breakdowns for commission vs. slippage to reveal which dominates

### Trade Markers on Equity Curve
Entries and exits are plotted directly on the equity curve as interactive markers:
- Green upward triangles (▲) mark buy entries
- Red downward triangles (▽) mark sell exits
- Click any marker to see a detail panel: ticker, side, entry/exit dates and prices, shares, commission, slippage, P&L

### 2D Parameter Heatmap
For any strategy with two tunable parameters, sweep a grid of values and visualize results as a color-coded heatmap:
- Configurable x/y parameter ranges (3–10 steps each, up to 100 cells)
- Supports any metric output: Sharpe ratio, CAGR, total return, max drawdown
- Red→yellow→green color scale, best-cell star marker, hover tooltip
- Reveals ridgelines of parameter robustness vs. overfit islands

### Walk-Forward Analysis
Test whether a strategy generalizes to unseen data using rolling IS/OOS folds:
- Configurable fold count (2–10) and train/test split (50–90%)
- Per-fold IS Sharpe vs. OOS Sharpe with pass/fail indicators
- **Sharpe Efficiency** = avg OOS Sharpe ÷ avg IS Sharpe — values near 1.0 indicate robustness
- Stitched OOS equity curve overlaid against the full IS curve

### Real-Time WebSocket Progress
Backtests stream progress events via WebSocket as the simulation runs:
- Live progress bar with current percentage
- Current simulation date and live equity value updating in real time
- Bar counter (N / total bars processed)
- Immediate redirect to results page on completion

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              FRONTEND (Next.js 14)           │
│  Dashboard │ Backtest │ Results │ Compare    │
│  Heatmap   │ Walk-Forward                   │
└────────────────────┬────────────────────────┘
                     │ REST API + WebSocket
┌────────────────────▼────────────────────────┐
│              BACKEND (FastAPI)               │
│  Data Ingestion │ Backtest Engine            │
│  Analytics      │ Strategy Registry          │
│  Walk-Forward   │ Parameter Sweep            │
└────────────────────┬────────────────────────┘
                     │ asyncpg
┌────────────────────▼────────────────────────┐
│           PostgreSQL 15 (Docker)             │
│  price_data │ backtest_runs │ trade_records  │
└─────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│           External Data (yfinance)           │
└─────────────────────────────────────────────┘
```

### Backtest Data Flow

```
User configures strategy
  → WebSocket /api/backtest/ws
    → Fetch/validate OHLCV data (yfinance → PostgreSQL cache)
    → Initialize portfolio ($100k default)
    → For each trading day:
        → Feed bar to strategy (only historical data — no lookahead)
        → Strategy emits signal (BUY weight / SELL fraction / HOLD)
        → Position sizing applies max_position_pct constraint
        → Execution simulator applies slippage + commission + volume limit
        → Portfolio updates cash, positions, equity
        → Stream progress event via WebSocket (every ~1% of bars)
    → Compute 25+ analytics on completed equity curve
    → Build clean (frictionless) equity curve alongside actual
    → Persist to database
    → Send completion event with backtest ID
    → Frontend redirects to full tear sheet
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, TanStack Query, Zustand |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| Data | pandas, numpy, scipy, yfinance |
| Database | PostgreSQL 15 |
| Infrastructure | Docker, GitHub Actions CI |

---

## Project Structure

```
quant-lab/
├── docker-compose.yml
├── .github/workflows/
│   ├── backend-ci.yml        # Runs pytest on every push to backend/
│   └── frontend-ci.yml       # Runs lint + build on every push to frontend/
│
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py           # FastAPI app factory + lifespan
│   │   ├── config.py         # Settings via pydantic-settings
│   │   ├── database.py       # Async SQLAlchemy engine + auto-migrations
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── api/              # Route handlers (data, backtest, strategies, analytics)
│   │   ├── services/
│   │   │   ├── backtest_engine.py   # Core event-driven loop + progress callback
│   │   │   ├── portfolio.py         # Portfolio state manager
│   │   │   ├── execution.py         # Slippage + commission simulator
│   │   │   ├── analytics.py         # All risk/performance metrics
│   │   │   ├── data_ingestion.py    # yfinance → PostgreSQL (batched upserts)
│   │   │   ├── walk_forward.py      # Rolling IS/OOS fold analysis
│   │   │   └── strategy_registry.py
│   │   └── strategies/
│   │       ├── sma_crossover.py
│   │       ├── mean_reversion.py
│   │       ├── momentum.py
│   │       └── pairs_trading.py
│   └── tests/                # 39 unit tests
│
└── frontend/
    └── src/
        ├── app/              # Next.js pages (dashboard, backtest, results, compare, data, strategies)
        │   └── backtest/
        │       └── [id]/
        │           ├── heatmap/      # 2D parameter sweep heatmap
        │           └── walkforward/  # Walk-forward analysis
        ├── components/       # Charts, analytics, backtest form, layout
        │   └── charts/
        │       ├── EquityCurve.tsx         # With interactive trade markers
        │       └── ParameterHeatmap.tsx    # 2D color-coded heatmap
        ├── hooks/            # useBacktest, useBacktestProgress, useMarketData
        └── lib/              # API client, TypeScript types, formatters
```

---

## Strategies

### 1. SMA Crossover (`sma_crossover`) — Trend Following
Buys when the short-term SMA crosses above the long-term SMA (golden cross). Sells on the inverse (death cross).

**Parameters:** `short_window` (5–100), `long_window` (10–300), `position_weight` (0.1–1.0)

**When it works:** Strong trending markets (2017 crypto, 2020–2021 equities).
**When it fails:** Choppy, range-bound markets — generates many false signals.

---

### 2. Mean Reversion / Bollinger Bands (`mean_reversion`) — Mean Reversion
Buys when price drops below the lower Bollinger Band (oversold). Sells when it rises above the upper band (overbought).

**Parameters:** `lookback` (10–100), `num_std` (0.5–4.0), `position_weight` (0.1–1.0)

**When it works:** Range-bound, high-volatility assets (commodity ETFs, individual stocks).
**When it fails:** Strongly trending assets — "oversold" keeps getting cheaper.

---

### 3. Cross-Sectional Momentum (`momentum`) — Momentum
Ranks all tickers by trailing return. Holds the top N performers. Rotates out of laggards.

**Parameters:** `lookback_days` (20–365), `top_n` (1–20), `skip_days` (0–30), `position_weight` (0.1–1.0)

**When it works:** Large diversified universes during trending markets.
**When it fails:** Momentum crashes (March 2020, 2022 reversal).

---

### 4. Statistical Pairs Trading (`pairs_trading`) — Statistical Arbitrage
Computes the log price ratio (spread) between two correlated assets. Enters when the z-score exceeds the entry threshold. Exits when it reverts to the mean. **Requires exactly 2 tickers.**

**Parameters:** `lookback` (20–252), `entry_z` (1.0–4.0), `exit_z` (0.0–2.0), `position_weight` (0.1–0.5)

**When it works:** Highly correlated pairs (GLD/GDX, XLF/KBE, SPY/IVV).
**When it fails:** Structural breaks in the pair relationship.

---

## Performance Metrics

| Category | Metrics |
|---|---|
| Returns | Total Return, CAGR, Annualized Return |
| Risk | Annualized Volatility, Max Drawdown, Max DD Duration, Current DD |
| Risk-Adjusted | Sharpe, Sortino, Calmar, Information Ratio |
| Tail Risk | VaR (95%), CVaR (95%), Skewness, Kurtosis |
| Trade Stats | Win Rate, Avg Win/Loss, Profit Factor, Avg Holding Period |
| Benchmark | Alpha, Beta, Correlation, Tracking Error |
| Transaction Costs | Total Commission, Total Slippage, Cost Drag (bps), Cost Drag (%) |
| Exposure | Avg Exposure %, Max Exposure % |

---

## API Reference

Base URL: `http://localhost:8000/api`
Interactive docs: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/data/tickers` | List all loaded tickers |
| `POST` | `/data/load` | Fetch + cache OHLCV data from yfinance |
| `GET` | `/data/ohlcv` | Query price data for charting (server-side downsampled to 500 pts) |
| `GET` | `/strategies/list` | List all available strategies |
| `GET` | `/strategies/{id}/params` | Get parameter schema for a strategy |
| `POST` | `/backtest/run` | Run a full backtest (HTTP) |
| `WS` | `/backtest/ws` | Run a backtest with real-time progress streaming |
| `GET` | `/backtest/list` | List all past backtests |
| `GET` | `/backtest/{id}` | Get full backtest result + trades |
| `DELETE` | `/backtest/{id}` | Delete a backtest |
| `POST` | `/backtest/sweep` | 1D parameter sensitivity sweep |
| `POST` | `/backtest/sweep2d` | 2D parameter grid sweep (heatmap) |
| `POST` | `/backtest/walk-forward` | Run walk-forward IS/OOS fold analysis |
| `POST` | `/analytics/compare` | Compare multiple backtests |
| `POST` | `/analytics/monte-carlo/{id}` | Run Monte Carlo simulation |
| `GET` | `/analytics/export/{id}` | Export results as CSV |

---

## Running Locally

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- Python 3.11+
- Node.js 20+

---

### Step 1 — Clone and start the database

```bash
git clone https://github.com/Ntalatam/quant-lab.git
cd quant-lab

# Start PostgreSQL on port 5433
docker compose up db -d
```

Verify it's healthy:
```bash
docker ps
# Should show: quant-lab-db-1   Up X seconds (healthy)   0.0.0.0:5433->5432/tcp
```

---

### Step 2 — Set up and start the backend

```bash
cd backend

# Create virtual environment (first time only)
python3 -m venv .venv

# Activate it
source .venv/bin/activate       # Mac/Linux
# .venv\Scripts\activate        # Windows

# Install dependencies (first time only)
pip install -e ".[test]"

# Create the .env file (first time only)
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://quantlab:quantlab@localhost:5433/quantlab
CORS_ORIGINS=["http://localhost:3000"]
EOF

# Start the server
uvicorn app.main:app --reload
```

Expected output:
```
INFO: Application startup complete.
```

Verify at: **http://localhost:8000/docs** — should show "QuantLab API" with all routes.

---

### Step 3 — Start the frontend

Open a **new terminal**:

```bash
cd quant-lab/frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

Open: **http://localhost:3000**

---

### Quick Start After Initial Setup

On subsequent runs, you only need three commands (one per terminal):

```bash
# Terminal 1 — from quant-lab/
docker compose up db -d

# Terminal 2 — from quant-lab/backend/
source .venv/bin/activate && uvicorn app.main:app --reload

# Terminal 3 — from quant-lab/frontend/
npm run dev
```

---

## Running Tests

```bash
cd quant-lab/backend
source .venv/bin/activate
pytest tests/ -v
```

Expected: **39 passed**

The test suite covers:
- `test_portfolio.py` — buy/sell execution, cash constraints, avg cost basis, equity calculation
- `test_execution.py` — slippage direction, volume constraints, commission math, price clamping
- `test_analytics.py` — Sharpe ratio, max drawdown, VaR, monthly returns, Monte Carlo
- `test_strategies.py` — golden cross/death cross signals, mean reversion bands, momentum ranking, pairs z-score

---

## Using the App

### Running Your First Backtest

1. Go to **http://localhost:3000/data** and load some tickers (e.g., `AAPL`, `MSFT`, `SPY`) for a date range
2. Go to **New Backtest** in the sidebar
3. Select a strategy, configure parameters, pick your tickers and date range
4. Click **Run Backtest** — watch the live progress bar stream equity in real time
5. Results appear automatically with the full tear sheet on completion

### Exploring Transaction Costs

In the **Performance** tab of any backtest, scroll below the equity curve to see the **Transaction Cost Breakdown**. The dashed blue line on the equity chart shows frictionless performance. The gap is your true cost drag.

### Analyzing Individual Trades

Click any green ▲ or red ▽ marker on the equity curve to open the trade detail panel — entry/exit dates, prices, shares, commission, slippage, and P&L.

### Testing Parameter Robustness

From any backtest result, click **2D Heatmap** in the top-right. Select two parameters, set their ranges and step count, pick a metric, and run. The color map shows which parameter combinations are robust vs. overfit.

### Walk-Forward Out-of-Sample Testing

From any backtest result, click **Walk-Forward**. Configure fold count and train/test split, then run. A **Sharpe Efficiency** near 1.0 means the strategy performs similarly on unseen data — a signal it's not just curve-fit.

### Pairs Trading Setup

Pairs trading requires **exactly 2 tickers**. Good pairs to try:
- `GLD` / `GDX` (gold spot vs. gold miners)
- `SPY` / `IVV` (two S&P 500 ETFs)
- `XLF` / `KBE` (financials vs. banks)

### Comparing Strategies

1. Run multiple backtests across different strategies or parameter sets
2. Go to **Compare** in the sidebar
3. Select 2+ backtests to overlay equity curves, compare metrics, and view the return correlation matrix

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'app'` | Running uvicorn from wrong directory | `cd backend` first |
| `npm error: Cannot find package.json` | Running npm from wrong directory | `cd frontend` first |
| `password authentication failed for user "quantlab"` | Docker postgres not running | `docker compose up db -d` |
| `Address already in use` on port 8000 | Another server occupying port 8000 | `lsof -i :8000` then `kill <PID>` |
| `localhost:8000` shows `{"detail":"Not Found"}` | Normal — no route at `/` | Use `/docs` or `/api/*` routes |
| Port 5432 conflict | Local Postgres.app running | Project uses port **5433** — no action needed |
| WebSocket connection failed | Backend not running or CORS | Ensure `uvicorn` is running on port 8000 |

---

## CI/CD

GitHub Actions runs on every push:

- **Backend CI** — installs dependencies, runs full pytest suite
- **Frontend CI** — runs ESLint and `next build`

Status badges reflect the latest commit on `main`.
