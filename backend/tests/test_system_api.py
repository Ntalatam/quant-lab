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


class _FailingEngine:
    def connect(self):
        raise RuntimeError("database unavailable")


class _FakePaperManager:
    def __init__(self, *_args, **_kwargs):
        self._summary = {
            "runtime_sessions": 1,
            "subscriber_channels": 2,
        }

    async def resume_active_sessions(self):
        return None

    async def shutdown(self):
        return None

    def health_summary(self):
        return self._summary


async def _noop():
    return None


def _build_client(monkeypatch, engine):
    monkeypatch.setattr(app_main, "init_db", _noop)
    monkeypatch.setattr(app_main, "PaperTradingManager", _FakePaperManager)
    monkeypatch.setattr(app_main, "engine", engine)
    return TestClient(app_main.create_app())


def test_health_endpoint_reports_ready_state(monkeypatch):
    with _build_client(monkeypatch, _HealthyEngine()) as client:
        response = client.get("/health", headers={"x-request-id": "req_health_ok"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_health_ok"
    assert float(response.headers["x-process-time-ms"]) >= 0

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["request_id"] == "req_health_ok"
    assert payload["dependencies"]["database"]["status"] == "ok"
    assert payload["dependencies"]["paper_trading"]["details"] == {
        "runtime_sessions": 1,
        "subscriber_channels": 2,
    }


def test_health_endpoint_reports_degraded_database(monkeypatch):
    with _build_client(monkeypatch, _FailingEngine()) as client:
        response = client.get("/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["database"]["status"] == "degraded"
    assert "database unavailable" in payload["dependencies"]["database"]["details"]["error"]
