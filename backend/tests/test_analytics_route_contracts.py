from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as app_main
from app.api import analytics as analytics_api
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


async def _noop():
    return None


def _build_client(monkeypatch):
    async def _get_db_override():
        yield object()

    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", _HealthyEngine())
    app = app_main.create_app()
    app.dependency_overrides[analytics_api.get_db] = _get_db_override
    install_auth_overrides(app)
    return TestClient(app)


def test_capacity_analysis_route_returns_typed_payload(monkeypatch):
    async def fake_build_capacity_analysis(db, backtest_id, workspace_id):
        assert backtest_id == "bt-capacity"
        assert workspace_id == "ws_test"
        return {
            "initial_capital": 100000.0,
            "n_trades": 12,
            "max_adv_participation_pct": 0.82,
            "avg_adv_participation_pct": 0.31,
            "p90_adv_participation_pct": 0.64,
            "capacity_estimates": [
                {
                    "adv_threshold_pct": 1.0,
                    "capacity_aum": 121951,
                    "label": "Max trade uses <=1.0% of ADV",
                }
            ],
            "trade_adv_stats": [
                {
                    "ticker": "AAPL",
                    "side": "BUY",
                    "date": "2024-03-12",
                    "shares": 125,
                    "notional": 23125.0,
                    "adv": 2810000.0,
                    "adv_participation_pct": 0.823,
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.analytics_execution.build_capacity_analysis",
        fake_build_capacity_analysis,
    )

    with _build_client(monkeypatch) as client:
        response = client.post("/api/analytics/capacity/bt-capacity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["n_trades"] == 12
    assert payload["capacity_estimates"][0]["capacity_aum"] == 121951
    assert payload["trade_adv_stats"][0]["ticker"] == "AAPL"


def test_transaction_cost_analysis_route_returns_typed_payload(monkeypatch):
    async def fake_build_transaction_cost_analysis(db, backtest_id, workspace_id):
        assert backtest_id == "bt-tca"
        assert workspace_id == "ws_test"
        return {
            "model": {
                "market_impact_model": "almgren_chriss",
                "max_volume_participation_pct": 5.0,
                "slippage_bps": 5.0,
                "commission_per_share": 0.005,
            },
            "summary": {
                "total_trades": 8,
                "total_commission": 12.45,
                "total_spread_cost": 9.2,
                "total_market_impact_cost": 18.7,
                "total_timing_cost": 6.8,
                "total_opportunity_cost": 1.5,
                "total_borrow_cost": 0.0,
                "total_locate_fees": 0.0,
                "total_implementation_shortfall": 48.65,
                "avg_fill_rate_pct": 96.4,
                "avg_participation_rate_pct": 1.12,
                "p90_participation_rate_pct": 1.84,
                "cost_as_pct_of_initial_capital": 0.049,
            },
            "ticker_breakdown": [
                {
                    "ticker": "MSFT",
                    "trades": 4,
                    "total_commission": 6.0,
                    "total_spread_cost": 4.3,
                    "total_market_impact_cost": 9.1,
                    "total_timing_cost": 2.4,
                    "total_opportunity_cost": 0.7,
                    "total_implementation_shortfall": 22.5,
                    "avg_fill_rate_pct": 95.5,
                    "avg_participation_rate_pct": 1.03,
                }
            ],
            "top_cost_trades": [
                {
                    "id": "trade-1",
                    "ticker": "MSFT",
                    "side": "BUY",
                    "position_direction": "LONG",
                    "date": "2024-03-12",
                    "shares": 50,
                    "requested_shares": 55,
                    "unfilled_shares": 5,
                    "commission": 1.2,
                    "spread_cost": 0.8,
                    "market_impact_cost": 2.1,
                    "timing_cost": 0.4,
                    "opportunity_cost": 0.1,
                    "implementation_shortfall": 4.6,
                    "fill_rate_pct": 90.91,
                    "participation_rate_pct": 1.45,
                    "risk_event": None,
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.analytics_execution.build_transaction_cost_analysis",
        fake_build_transaction_cost_analysis,
    )

    with _build_client(monkeypatch) as client:
        response = client.post("/api/analytics/tca/bt-tca")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_implementation_shortfall"] == 48.65
    assert payload["ticker_breakdown"][0]["ticker"] == "MSFT"
    assert payload["top_cost_trades"][0]["id"] == "trade-1"


def test_regime_analysis_route_returns_typed_payload(monkeypatch):
    async def fake_build_regime_analysis(db, backtest_id, workspace_id):
        assert backtest_id == "bt-regime"
        assert workspace_id == "ws_test"
        return {
            "timeline": [
                {"date": "2024-03-01", "regime": "Trending", "return": 0.012},
                {"date": "2024-03-04", "regime": "Neutral", "return": -0.004},
            ],
            "regime_stats": [
                {
                    "regime": "Trending",
                    "color": "#4488ff",
                    "days": 1,
                    "pct_of_period": 50.0,
                    "ann_return_pct": 302.4,
                    "ann_volatility_pct": 0.0,
                    "sharpe": 0.0,
                }
            ],
            "description": "Mixed regime environment — strategy performance may vary across sub-periods.",
        }

    monkeypatch.setattr(
        "app.api.analytics_factor_regime.build_regime_analysis",
        fake_build_regime_analysis,
    )

    with _build_client(monkeypatch) as client:
        response = client.post("/api/analytics/regime-analysis/bt-regime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["timeline"][0]["regime"] == "Trending"
    assert payload["timeline"][0]["return"] == 0.012
    assert payload["regime_stats"][0]["color"] == "#4488ff"


def test_factor_exposure_route_returns_typed_payload(monkeypatch):
    async def fake_build_factor_exposure(db, backtest_id, workspace_id):
        assert backtest_id == "bt-factor"
        assert workspace_id == "ws_test"
        return {
            "alpha_annualized": 4.2145,
            "r_squared": 0.6123,
            "n_obs": 84,
            "factors": [
                {
                    "name": "Market",
                    "beta": 0.7821,
                    "t_stat": 3.41,
                    "p_value": 0.0012,
                    "significant": True,
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.analytics_factor_regime.build_factor_exposure",
        fake_build_factor_exposure,
    )

    with _build_client(monkeypatch) as client:
        response = client.post("/api/analytics/factor-exposure/bt-factor")

    assert response.status_code == 200
    payload = response.json()
    assert payload["alpha_annualized"] == 4.2145
    assert payload["factors"][0]["name"] == "Market"
    assert payload["factors"][0]["significant"] is True


def test_correlation_route_returns_typed_payload(monkeypatch):
    async def fake_build_correlation_response(db, payload):
        assert payload.tickers == ["AAPL", "MSFT", "QQQ"]
        return {
            "tickers": ["AAPL", "MSFT", "QQQ"],
            "static_matrix": [
                [1.0, 0.76, 0.81],
                [0.76, 1.0, 0.69],
                [0.81, 0.69, 1.0],
            ],
            "rolling_correlations": [
                {
                    "pair": "AAPL/MSFT",
                    "ticker_a": "AAPL",
                    "ticker_b": "MSFT",
                    "series": [{"date": "2024-03-01", "value": 0.71}],
                }
            ],
            "discovered_pairs": [
                {
                    "ticker_a": "AAPL",
                    "ticker_b": "MSFT",
                    "adf_statistic": -3.11,
                    "adf_pvalue": 0.0321,
                    "cointegrated": True,
                    "beta": 0.93,
                    "half_life_days": 14.5,
                    "current_zscore": 1.24,
                    "spread_std": 0.0432,
                }
            ],
        }

    monkeypatch.setattr(
        "app.api.analytics_market.build_correlation_response",
        fake_build_correlation_response,
    )

    with _build_client(monkeypatch) as client:
        response = client.post(
            "/api/analytics/correlation",
            json={
                "tickers": ["AAPL", "MSFT", "QQQ"],
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "rolling_window": 21,
                "max_pairs": 5,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tickers"] == ["AAPL", "MSFT", "QQQ"]
    assert payload["rolling_correlations"][0]["pair"] == "AAPL/MSFT"
    assert payload["discovered_pairs"][0]["cointegrated"] is True


def test_spread_route_returns_typed_payload(monkeypatch):
    async def fake_build_spread_response(db, payload):
        assert payload.ticker_a == "AAPL"
        assert payload.ticker_b == "MSFT"
        return {
            "ticker_a": "AAPL",
            "ticker_b": "MSFT",
            "spread_series": [{"date": "2024-03-01", "value": 0.0142}],
            "zscore_series": [{"date": "2024-03-01", "value": 1.11}],
            "half_life_days": 18.4,
            "current_zscore": 1.11,
            "spread_mean": 0.0021,
            "spread_std": 0.0314,
            "cointegration": {
                "ticker_a": "AAPL",
                "ticker_b": "MSFT",
                "adf_statistic": -3.02,
                "adf_pvalue": 0.0412,
                "cointegrated": True,
                "beta": 1.08,
                "half_life_days": 18.4,
                "current_zscore": 1.11,
                "spread_std": 0.0314,
            },
        }

    monkeypatch.setattr(
        "app.api.analytics_market.build_spread_response",
        fake_build_spread_response,
    )

    with _build_client(monkeypatch) as client:
        response = client.post(
            "/api/analytics/spread",
            json={
                "ticker_a": "AAPL",
                "ticker_b": "MSFT",
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "lookback": 21,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["half_life_days"] == 18.4
    assert payload["cointegration"]["beta"] == 1.08
    assert payload["spread_series"][0]["value"] == 0.0142
