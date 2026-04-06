from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main as app_main
from app.api import analytics as analytics_api
from app.services import risk_budget
from tests.auth_helpers import install_auth_overrides


class _FakeConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, _statement):
        return 1


class _HealthyEngine:
    def connect(self):
        return _FakeConnection()


class _FakePaperManager:
    def __init__(self, *_args, **_kwargs):
        pass

    async def resume_active_sessions(self):
        return None

    async def shutdown(self):
        return None

    def health_summary(self):
        return {
            "runtime_sessions": 0,
            "subscriber_channels": 0,
        }


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeDB:
    def __init__(self, run, trades):
        self._run = run
        self._trades = trades
        self.calls = 0

    async def execute(self, _statement):
        self.calls += 1
        if self.calls <= 2:
            return _ScalarResult([self._run])
        return _ScalarResult(self._trades)


async def _noop():
    return None


def _build_client(monkeypatch, fake_db):
    async def _get_db_override():
        yield fake_db

    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", _HealthyEngine())
    app = app_main.create_app()
    app.dependency_overrides[analytics_api.get_db] = _get_db_override
    install_auth_overrides(app)
    return TestClient(app)


def test_reconstruct_share_panel_tracks_long_and_short_lifecycle():
    date_index = risk_budget.pd.to_datetime(
        ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    )
    trades = [
        SimpleNamespace(
            ticker="AAPL",
            side="BUY",
            position_direction="LONG",
            entry_date="2024-01-02",
            exit_date=None,
            shares=10,
        ),
        SimpleNamespace(
            ticker="AAPL",
            side="SELL",
            position_direction="LONG",
            entry_date="2024-01-02",
            exit_date="2024-01-04",
            shares=4,
        ),
        SimpleNamespace(
            ticker="MSFT",
            side="SELL",
            position_direction="SHORT",
            entry_date="2024-01-03",
            exit_date=None,
            shares=6,
        ),
        SimpleNamespace(
            ticker="MSFT",
            side="BUY",
            position_direction="SHORT",
            entry_date="2024-01-03",
            exit_date="2024-01-05",
            shares=2,
        ),
    ]

    panel = risk_budget._reconstruct_share_panel(trades, date_index, ["AAPL", "MSFT"])

    assert panel.loc["2024-01-02", "AAPL"] == 10
    assert panel.loc["2024-01-04", "AAPL"] == 6
    assert panel.loc["2024-01-03", "MSFT"] == -6
    assert panel.loc["2024-01-05", "MSFT"] == -4


def test_risk_budget_endpoint_returns_typed_payload(monkeypatch):
    async def fake_build_risk_budget_response(db, backtest_id, workspace_id, lookback_days):
        assert backtest_id == "bt-risk"
        assert workspace_id == "ws_test"
        assert lookback_days == 63
        return {
            "summary": {
                "snapshot_date": "2024-03-01",
                "lookback_days": 63,
                "total_equity": 125000.0,
                "gross_exposure_pct": 97.4,
                "net_exposure_pct": 42.5,
                "daily_var_95_pct": 2.15,
                "daily_var_95_dollar": 2687.5,
                "daily_cvar_95_pct": 3.12,
                "daily_cvar_95_dollar": 3900.0,
                "diversification_ratio": 1.42,
                "average_pairwise_correlation": 0.34,
            },
            "positions": [
                {
                    "ticker": "AAPL",
                    "sector": "Technology",
                    "shares": 100,
                    "price": 185.0,
                    "market_value": 18500.0,
                    "weight_pct": 14.8,
                    "daily_volatility_pct": 1.92,
                    "beta_to_portfolio": 1.11,
                    "var_contribution": 540.25,
                    "var_contribution_pct": 20.1,
                    "cvar_contribution": 760.0,
                    "cvar_contribution_pct": 19.5,
                }
            ],
            "scenarios": [
                {
                    "id": "covid_2020",
                    "name": "COVID Crash",
                    "description": "Pandemic shock window.",
                    "start_date": "2020-02-19",
                    "end_date": "2020-03-23",
                    "portfolio_return_pct": -18.2,
                    "pnl_impact": -22750.0,
                    "average_pairwise_correlation": 0.71,
                    "correlation_shift": 0.37,
                    "top_pair": "AAPL/MSFT",
                    "top_pair_correlation": 0.89,
                    "position_impacts": [
                        {
                            "ticker": "AAPL",
                            "source_ticker": "AAPL",
                            "weight_pct": 14.8,
                            "scenario_return_pct": -22.1,
                            "pnl_impact": -4088.5,
                        }
                    ],
                }
            ],
        }

    fake_db = _FakeDB(run=SimpleNamespace(id="bt-risk"), trades=[])
    monkeypatch.setattr(
        "app.api.analytics_risk.build_risk_budget_response",
        fake_build_risk_budget_response,
    )

    with _build_client(monkeypatch, fake_db) as client:
        response = client.post("/api/analytics/risk-budget/bt-risk")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["daily_var_95_dollar"] == 2687.5
    assert payload["positions"][0]["ticker"] == "AAPL"
    assert payload["scenarios"][0]["id"] == "covid_2020"


def test_compute_component_risk_reports_positive_cvar_loss():
    returns_window = risk_budget.pd.DataFrame(
        {
            "AAPL": [-0.02, -0.01, 0.005, 0.004, -0.015],
            "MSFT": [-0.03, -0.012, 0.006, 0.005, -0.02],
        }
    )
    weights = risk_budget.pd.Series({"AAPL": 0.55, "MSFT": 0.45})

    result = risk_budget._compute_component_risk(
        returns_window=returns_window,
        weights=weights,
        equity_value=100_000,
    )

    assert result["portfolio_cvar_pct"] > 0
    assert result["portfolio_cvar_dollar"] > 0
