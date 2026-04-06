from __future__ import annotations

from app.models.paper import PaperTradingSession
from app.services.brokers.alpaca import AlpacaPaperBrokerAdapter
from app.services.brokers.base import BrokerAdapter
from app.services.brokers.paper import SimulatedPaperBrokerAdapter


def build_broker_adapter(
    *,
    execution_mode: str,
    broker_adapter: str,
) -> BrokerAdapter:
    if execution_mode == "simulated_paper" or broker_adapter == "paper":
        return SimulatedPaperBrokerAdapter()
    if broker_adapter == "alpaca":
        return AlpacaPaperBrokerAdapter()
    raise ValueError(f"Unsupported broker adapter: {broker_adapter}")


def build_broker_adapter_for_session(session: PaperTradingSession) -> BrokerAdapter:
    return build_broker_adapter(
        execution_mode=session.execution_mode,
        broker_adapter=session.broker_adapter,
    )
