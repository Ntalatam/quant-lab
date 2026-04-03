from __future__ import annotations

from fastapi.testclient import TestClient

from app import main as app_main


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
    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", _HealthyEngine())
    return TestClient(app_main.create_app())


def test_openapi_schema_exposes_curated_metadata(monkeypatch):
    with _build_client(monkeypatch) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()

    assert payload["info"]["title"] == "QuantLab API"
    assert "quantitative research" in payload["info"]["summary"].lower()
    assert {tag["name"] for tag in payload["tags"]} >= {
        "system",
        "data",
        "backtest",
        "analytics",
        "paper-trading",
        "strategies",
        "demo",
    }


def test_openapi_schema_includes_typed_route_contracts(monkeypatch):
    with _build_client(monkeypatch) as client:
        payload = client.get("/openapi.json").json()

    backtest_run = payload["paths"]["/api/backtest/run"]["post"]
    compare = payload["paths"]["/api/analytics/compare"]["post"]
    paper_create = payload["paths"]["/api/paper/sessions"]["post"]

    assert backtest_run["summary"] == "Run and persist a backtest"
    assert (
        backtest_run["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/BacktestResultResponse"
    )
    assert (
        compare["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/CompareRequest"
    )
    assert (
        compare["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ComparisonResponse"
    )
    assert (
        paper_create["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/PaperTradingSessionDetail"
    )


def test_swagger_docs_route_is_available(monkeypatch):
    with _build_client(monkeypatch) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()
