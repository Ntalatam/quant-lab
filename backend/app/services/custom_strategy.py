from __future__ import annotations

import ast
import hashlib
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_strategy import CustomStrategy
from app.schemas.strategy import StrategyEditorHelper
from app.strategies.base import BaseStrategy

CUSTOM_STRATEGY_ID_PREFIX = "custom_"
MAX_SOURCE_BYTES = 20_000
ALLOWED_SIGNAL_MODES = {"long_only", "long_short"}

EDITOR_RULES = [
    "Define a top-level STRATEGY dictionary with name, description, category, signal_mode, and params.",
    "Define generate_signals(data, current_date, tickers, params) and return a dict[ticker] -> signal.",
    "Signals must stay between -1.0 and 1.0. Negative signals only make sense for long/short strategies.",
    "Imports, attribute access, classes, and arbitrary builtins are blocked by design.",
    "Use the provided helpers like close(), sma(), ema(), rsi(), momentum(), top_n(), and bottom_n().",
]

EDITOR_TEMPLATE = """STRATEGY = {
    "name": "Custom Momentum Rotation",
    "description": "Ranks the universe by 63-day momentum and owns the strongest names.",
    "category": "momentum",
    "signal_mode": "long_only",
    "requires_short_selling": False,
    "params": [
        {
            "name": "lookback",
            "label": "Lookback",
            "type": "int",
            "default": 63,
            "min": 20,
            "max": 252,
            "step": 1,
            "description": "Momentum measurement window in bars.",
        },
        {
            "name": "top_n",
            "label": "Top N",
            "type": "int",
            "default": 2,
            "min": 1,
            "max": 10,
            "step": 1,
            "description": "How many leaders to own at each rebalance.",
        },
    ],
}


def generate_signals(data, current_date, tickers, params):
    scores = {}
    for ticker in tickers:
        prices = close(data, ticker)
        scores[ticker] = momentum(prices, params["lookback"])

    leaders = top_n(scores, params["top_n"])
    signals = {}
    for ticker in tickers:
        signals[ticker] = 1.0 / max(len(leaders), 1) if ticker in leaders else 0.0
    return signals
"""

HELPER_SPECS = [
    StrategyEditorHelper(
        name="close",
        signature="close(data, ticker)",
        description="Adjusted close series for one ticker as a numeric list.",
    ),
    StrategyEditorHelper(
        name="high",
        signature="high(data, ticker)",
        description="High-price series for one ticker.",
    ),
    StrategyEditorHelper(
        name="low",
        signature="low(data, ticker)",
        description="Low-price series for one ticker.",
    ),
    StrategyEditorHelper(
        name="volume",
        signature="volume(data, ticker)",
        description="Volume series for one ticker.",
    ),
    StrategyEditorHelper(
        name="latest",
        signature="latest(values, default=0.0)",
        description="Latest finite value from a numeric series.",
    ),
    StrategyEditorHelper(
        name="previous",
        signature="previous(values, default=0.0)",
        description="Previous finite value from a numeric series.",
    ),
    StrategyEditorHelper(
        name="sma",
        signature="sma(values, window)",
        description="Rolling simple moving average as a numeric list.",
    ),
    StrategyEditorHelper(
        name="ema",
        signature="ema(values, window)",
        description="Rolling exponential moving average as a numeric list.",
    ),
    StrategyEditorHelper(
        name="rsi",
        signature="rsi(values, window=14)",
        description="Relative Strength Index as a numeric list.",
    ),
    StrategyEditorHelper(
        name="stdev",
        signature="stdev(values, window)",
        description="Rolling standard deviation as a numeric list.",
    ),
    StrategyEditorHelper(
        name="zscore",
        signature="zscore(values, window)",
        description="Rolling z-score as a numeric list.",
    ),
    StrategyEditorHelper(
        name="pct_change",
        signature="pct_change(values, periods=1)",
        description="Percentage change series.",
    ),
    StrategyEditorHelper(
        name="momentum",
        signature="momentum(values, lookback)",
        description="Trailing percentage return over a lookback window.",
    ),
    StrategyEditorHelper(
        name="highest",
        signature="highest(values, window)",
        description="Highest observed value across the trailing window.",
    ),
    StrategyEditorHelper(
        name="lowest",
        signature="lowest(values, window)",
        description="Lowest observed value across the trailing window.",
    ),
    StrategyEditorHelper(
        name="crosses_above",
        signature="crosses_above(left, right)",
        description="True when left crosses above right on the latest bar.",
    ),
    StrategyEditorHelper(
        name="crosses_below",
        signature="crosses_below(left, right)",
        description="True when left crosses below right on the latest bar.",
    ),
    StrategyEditorHelper(
        name="top_n",
        signature="top_n(scores, n)",
        description="Top-N ticker ids from a score dictionary.",
    ),
    StrategyEditorHelper(
        name="bottom_n",
        signature="bottom_n(scores, n)",
        description="Bottom-N ticker ids from a score dictionary.",
    ),
    StrategyEditorHelper(
        name="clamp",
        signature="clamp(value, lower, upper)",
        description="Clamp a numeric value into a safe signal range.",
    ),
]

SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "sum": sum,
    "zip": zip,
}

FORBIDDEN_NODES = (
    ast.Attribute,
    ast.Import,
    ast.ImportFrom,
    ast.ClassDef,
    ast.AsyncFunctionDef,
    ast.Lambda,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.Raise,
    ast.Global,
    ast.Nonlocal,
    ast.Delete,
    ast.While,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
)

ALLOWED_NODES = {
    ast.Module,
    ast.Assign,
    ast.Expr,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.For,
    ast.If,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.Dict,
    ast.List,
    ast.Tuple,
    ast.Subscript,
    ast.Slice,
    ast.Index,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.IfExp,
    ast.ListComp,
    ast.DictComp,
    ast.comprehension,
    ast.keyword,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
    ast.In,
    ast.NotIn,
}


class CustomStrategyValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CustomStrategyMetadata:
    name: str
    description: str
    category: str
    signal_mode: str
    requires_short_selling: bool
    param_schema: list[dict[str, Any]]
    default_params: dict[str, int | float | str | bool]


@dataclass(frozen=True)
class CustomStrategyDefinition:
    strategy_id: str
    metadata: CustomStrategyMetadata
    code: str
    compiled_at: str
    runner: Any

    def instantiate(self, overrides: dict[str, Any] | None = None) -> BaseStrategy:
        return _CompiledCustomStrategyInstance(self, overrides or {})


class _SafetyValidator(ast.NodeVisitor):
    def __init__(self, helper_names: set[str]):
        self.helper_names = helper_names
        self.local_functions: set[str] = set()

    def validate(self, tree: ast.Module) -> None:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                self.local_functions.add(node.name)
        self.visit(tree)

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, FORBIDDEN_NODES):
            raise CustomStrategyValidationError(
                f"{node.__class__.__name__} is not allowed in custom strategies."
            )
        if type(node) not in ALLOWED_NODES:
            raise CustomStrategyValidationError(
                f"{node.__class__.__name__} is not supported in custom strategies."
            )
        super().generic_visit(node)

    def visit_Module(self, node: ast.Module) -> None:
        if not node.body:
            raise CustomStrategyValidationError("Strategy source is empty.")
        for statement in node.body:
            if not isinstance(statement, (ast.Assign, ast.FunctionDef)):
                if isinstance(statement, FORBIDDEN_NODES):
                    self.visit(statement)
                raise CustomStrategyValidationError(
                    "Only STRATEGY = {...} and function definitions are allowed at module scope."
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if not all(isinstance(target, (ast.Name, ast.Subscript)) for target in node.targets):
            raise CustomStrategyValidationError(
                "Only variable and dictionary assignments are supported."
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name.startswith("_"):
            raise CustomStrategyValidationError("Private helper functions are not allowed.")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("__"):
            raise CustomStrategyValidationError("Dunder names are not allowed.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            raise CustomStrategyValidationError(
                "Only direct helper calls are allowed. Attribute and method calls are blocked."
            )
        allowed_calls = self.helper_names | self.local_functions | set(SAFE_BUILTINS)
        if node.func.id not in allowed_calls:
            raise CustomStrategyValidationError(f"Call to '{node.func.id}' is not allowed.")
        self.generic_visit(node)


class _CompiledCustomStrategyInstance(BaseStrategy):
    def __init__(
        self,
        definition: CustomStrategyDefinition,
        overrides: dict[str, Any],
    ):
        self._definition = definition
        self.name = definition.metadata.name
        self.description = definition.metadata.description
        self.category = definition.metadata.category
        self.default_params = definition.metadata.default_params
        self.param_schema = definition.metadata.param_schema
        self.signal_mode = definition.metadata.signal_mode
        self.requires_short_selling = definition.metadata.requires_short_selling
        self.params = _coerce_params(self.param_schema, self.default_params, overrides)

    def generate_signals(
        self,
        data: dict[str, pd.DataFrame],
        current_date: pd.Timestamp,
    ) -> dict[str, float]:
        safe_data = _prepare_data_window(data)
        result = self._definition.runner(
            safe_data,
            current_date.isoformat(),
            list(data.keys()),
            dict(self.params),
        )
        if not isinstance(result, dict):
            raise CustomStrategyValidationError(
                "generate_signals must return a dictionary of ticker -> signal."
            )

        normalized: dict[str, float] = {}
        for ticker in data:
            value = result.get(ticker, 0.0)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise CustomStrategyValidationError(
                    f"Signal for {ticker} must be numeric, got {type(value).__name__}."
                )
            bounded = float(value)
            if not math.isfinite(bounded):
                raise CustomStrategyValidationError(f"Signal for {ticker} must be finite.")
            normalized[ticker] = clamp(bounded, -1.0, 1.0)
        return normalized


def get_editor_spec() -> dict[str, Any]:
    return {
        "template": EDITOR_TEMPLATE,
        "rules": EDITOR_RULES,
        "helpers": [helper.model_dump() for helper in HELPER_SPECS],
    }


def validate_custom_strategy_source(code: str) -> dict[str, Any]:
    metadata, runner = _compile_source(code)
    warnings: list[str] = []
    if metadata.signal_mode == "long_short" and not metadata.requires_short_selling:
        warnings.append("Long/short strategies automatically require short-selling support.")

    _dry_run_strategy(runner, metadata.default_params)
    preview = _metadata_to_strategy_info("draft", metadata, source_type="custom")
    extracted = {
        "id": "draft",
        "name": metadata.name,
        "source_type": "custom",
        "params": metadata.param_schema,
        "defaults": metadata.default_params,
    }
    return {
        "valid": True,
        "errors": [],
        "warnings": warnings,
        "preview": preview,
        "extracted": extracted,
    }


async def list_custom_strategy_records(db: AsyncSession) -> list[CustomStrategy]:
    result = await db.execute(
        select(CustomStrategy).order_by(
            CustomStrategy.updated_at.desc(), CustomStrategy.created_at.desc()
        )
    )
    return result.scalars().all()


async def get_custom_strategy_record(
    db: AsyncSession,
    strategy_id: str,
) -> CustomStrategy | None:
    return await db.get(CustomStrategy, strategy_id)


async def create_custom_strategy(
    db: AsyncSession,
    code: str,
) -> CustomStrategy:
    metadata, _runner = _compile_source(code)
    now = datetime.now(UTC).replace(tzinfo=None)
    strategy = CustomStrategy(
        id=f"{CUSTOM_STRATEGY_ID_PREFIX}{uuid.uuid4().hex[:12]}",
        name=metadata.name,
        description=metadata.description,
        category=metadata.category,
        signal_mode=metadata.signal_mode,
        requires_short_selling=metadata.requires_short_selling,
        code=code,
        param_schema=metadata.param_schema,
        default_params=metadata.default_params,
        created_at=now,
        updated_at=now,
    )
    db.add(strategy)
    await db.flush()
    return strategy


async def update_custom_strategy(
    db: AsyncSession,
    strategy: CustomStrategy,
    code: str,
) -> CustomStrategy:
    metadata, _runner = _compile_source(code)
    strategy.name = metadata.name
    strategy.description = metadata.description
    strategy.category = metadata.category
    strategy.signal_mode = metadata.signal_mode
    strategy.requires_short_selling = metadata.requires_short_selling
    strategy.code = code
    strategy.param_schema = metadata.param_schema
    strategy.default_params = metadata.default_params
    strategy.updated_at = datetime.now(UTC).replace(tzinfo=None)
    await db.flush()
    return strategy


async def delete_custom_strategy(db: AsyncSession, strategy: CustomStrategy) -> None:
    await db.delete(strategy)
    await db.flush()


def strategy_record_to_info(strategy: CustomStrategy) -> dict[str, Any]:
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "category": strategy.category,
        "source_type": "custom",
        "signal_mode": strategy.signal_mode,
        "requires_short_selling": strategy.requires_short_selling,
        "params": strategy.param_schema,
    }


def strategy_record_to_detail(strategy: CustomStrategy) -> dict[str, Any]:
    return {
        **strategy_record_to_info(strategy),
        "defaults": strategy.default_params,
        "code": strategy.code,
        "created_at": strategy.created_at.isoformat(),
        "updated_at": strategy.updated_at.isoformat(),
    }


def strategy_record_to_summary(strategy: CustomStrategy) -> dict[str, Any]:
    return {
        **strategy_record_to_info(strategy),
        "created_at": strategy.created_at.isoformat(),
        "updated_at": strategy.updated_at.isoformat(),
    }


async def build_custom_strategy_definition(
    db: AsyncSession,
    strategy_id: str,
) -> CustomStrategyDefinition:
    record = await get_custom_strategy_record(db, strategy_id)
    if record is None:
        raise ValueError(f"Custom strategy {strategy_id} was not found.")
    return _compile_strategy_record(record)


def _compile_strategy_record(record: CustomStrategy) -> CustomStrategyDefinition:
    cache_key = f"{record.id}:{record.updated_at.isoformat()}:{hashlib.sha256(record.code.encode()).hexdigest()}"
    cached = _COMPILED_CACHE.get(cache_key)
    if cached is not None:
        return cached

    metadata, runner = _compile_source(record.code)
    definition = CustomStrategyDefinition(
        strategy_id=record.id,
        metadata=metadata,
        code=record.code,
        compiled_at=cache_key,
        runner=runner,
    )
    _COMPILED_CACHE.clear()
    _COMPILED_CACHE[cache_key] = definition
    return definition


_COMPILED_CACHE: dict[str, CustomStrategyDefinition] = {}


def _compile_source(code: str) -> tuple[CustomStrategyMetadata, Any]:
    source = code.strip()
    if not source:
        raise CustomStrategyValidationError("Strategy source cannot be empty.")
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise CustomStrategyValidationError(
            f"Strategy source exceeds the {MAX_SOURCE_BYTES} byte limit."
        )

    tree = ast.parse(source, mode="exec")
    _SafetyValidator(_helper_globals().keys()).validate(tree)

    strategy_literal = _extract_strategy_literal(tree)
    metadata = _parse_metadata(strategy_literal)

    env = {"__builtins__": {}}
    env.update(SAFE_BUILTINS)
    env.update(_helper_globals())
    exec(compile(tree, "<custom-strategy>", "exec"), env, env)

    runner = env.get("generate_signals")
    if not callable(runner):
        raise CustomStrategyValidationError(
            "Custom strategy must define generate_signals(data, current_date, tickers, params)."
        )
    return metadata, runner


def _extract_strategy_literal(tree: ast.Module) -> dict[str, Any]:
    strategy_node: ast.Assign | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise CustomStrategyValidationError(
                    "Only STRATEGY = {...} is allowed at module scope."
                )
            if node.targets[0].id == "STRATEGY":
                strategy_node = node
                break
    if strategy_node is None:
        raise CustomStrategyValidationError("Define a top-level STRATEGY dictionary.")
    try:
        value = ast.literal_eval(strategy_node.value)
    except Exception as exc:
        raise CustomStrategyValidationError(
            "STRATEGY metadata must be a plain Python literal dictionary."
        ) from exc
    if not isinstance(value, dict):
        raise CustomStrategyValidationError("STRATEGY must evaluate to a dictionary.")
    return value


def _parse_metadata(raw: dict[str, Any]) -> CustomStrategyMetadata:
    name = _require_string(raw, "name")
    description = _require_string(raw, "description")
    category = _require_string(raw, "category")
    signal_mode = _require_string(raw, "signal_mode")
    if signal_mode not in ALLOWED_SIGNAL_MODES:
        raise CustomStrategyValidationError(
            "signal_mode must be either 'long_only' or 'long_short'."
        )
    raw_params = raw.get("params", [])
    if not isinstance(raw_params, list):
        raise CustomStrategyValidationError("STRATEGY['params'] must be a list.")

    param_schema: list[dict[str, Any]] = []
    default_params: dict[str, int | float | str | bool] = {}
    seen_names: set[str] = set()
    for item in raw_params:
        if not isinstance(item, dict):
            raise CustomStrategyValidationError("Each param definition must be a dictionary.")
        name_key = _require_string(item, "name")
        if name_key in seen_names:
            raise CustomStrategyValidationError(f"Duplicate param name '{name_key}'.")
        seen_names.add(name_key)

        param_type = _require_string(item, "type")
        if param_type not in {"int", "float", "select", "bool"}:
            raise CustomStrategyValidationError(
                f"Param '{name_key}' has unsupported type '{param_type}'."
            )

        definition = {
            "name": name_key,
            "label": _require_string(item, "label"),
            "type": param_type,
            "default": item.get("default"),
            "min": item.get("min"),
            "max": item.get("max"),
            "step": item.get("step"),
            "options": item.get("options"),
            "description": _require_string(item, "description"),
        }
        coerced_default = _coerce_param_value(definition, item.get("default"))
        definition["default"] = coerced_default
        default_params[name_key] = coerced_default
        param_schema.append(definition)

    requires_short_selling = bool(raw.get("requires_short_selling", False))
    if signal_mode == "long_short":
        requires_short_selling = True

    return CustomStrategyMetadata(
        name=name,
        description=description,
        category=category,
        signal_mode=signal_mode,
        requires_short_selling=requires_short_selling,
        param_schema=param_schema,
        default_params=default_params,
    )


def _require_string(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CustomStrategyValidationError(f"STRATEGY['{key}'] must be a non-empty string.")
    return value.strip()


def _coerce_params(
    param_schema: list[dict[str, Any]],
    default_params: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, int | float | str | bool]:
    values = dict(default_params)
    for definition in param_schema:
        key = definition["name"]
        if key in overrides:
            values[key] = _coerce_param_value(definition, overrides[key])
    return values


def _coerce_param_value(definition: dict[str, Any], value: Any) -> int | float | str | bool:
    param_type = definition["type"]
    if param_type == "int":
        coerced = int(value)
    elif param_type == "float":
        coerced = float(value)
    elif param_type == "bool":
        if isinstance(value, bool):
            coerced = value
        else:
            coerced = str(value).lower() in {"1", "true", "yes", "on"}
    else:
        coerced = str(value)

    if param_type == "select":
        options = definition.get("options") or []
        if options and coerced not in options:
            raise CustomStrategyValidationError(
                f"Param '{definition['name']}' must be one of {options}."
            )

    minimum = definition.get("min")
    maximum = definition.get("max")
    if minimum is not None and isinstance(coerced, (int, float)) and coerced < minimum:
        raise CustomStrategyValidationError(f"Param '{definition['name']}' must be >= {minimum}.")
    if maximum is not None and isinstance(coerced, (int, float)) and coerced > maximum:
        raise CustomStrategyValidationError(f"Param '{definition['name']}' must be <= {maximum}.")
    return coerced


def _metadata_to_strategy_info(
    strategy_id: str,
    metadata: CustomStrategyMetadata,
    *,
    source_type: str,
) -> dict[str, Any]:
    return {
        "id": strategy_id,
        "name": metadata.name,
        "description": metadata.description,
        "category": metadata.category,
        "source_type": source_type,
        "signal_mode": metadata.signal_mode,
        "requires_short_selling": metadata.requires_short_selling,
        "params": metadata.param_schema,
    }


def _dry_run_strategy(
    runner: Any,
    default_params: dict[str, Any],
) -> None:
    tickers = ["AAPL", "MSFT", "SPY"]
    idx = pd.bdate_range("2024-01-02", periods=120)
    data: dict[str, dict[str, list[float]]] = {}
    for offset, ticker in enumerate(tickers):
        base = np.linspace(100 + offset * 5, 120 + offset * 8, len(idx))
        seasonal = np.sin(np.linspace(0, 5, len(idx))) * (offset + 1)
        prices = base + seasonal
        volume_series = np.linspace(900_000 + offset * 50_000, 1_400_000, len(idx))
        data[ticker] = {
            "open": prices.tolist(),
            "high": (prices * 1.01).tolist(),
            "low": (prices * 0.99).tolist(),
            "close": prices.tolist(),
            "adj_close": prices.tolist(),
            "volume": volume_series.tolist(),
        }

    result = runner(data, idx[-1].isoformat(), tickers, dict(default_params))
    if not isinstance(result, dict):
        raise CustomStrategyValidationError(
            "generate_signals must return a dict during validation."
        )


def _prepare_data_window(data: dict[str, pd.DataFrame]) -> dict[str, dict[str, list[float]]]:
    prepared: dict[str, dict[str, list[float]]] = {}
    for ticker, frame in data.items():
        prepared[ticker] = {
            "open": _series_to_list(frame["open"]),
            "high": _series_to_list(frame["high"]),
            "low": _series_to_list(frame["low"]),
            "close": _series_to_list(frame["close"]),
            "adj_close": _series_to_list(frame["adj_close"]),
            "volume": _series_to_list(frame["volume"]),
        }
    return prepared


def _series_to_list(series: pd.Series) -> list[float]:
    clean = pd.Series(series, dtype="float64").replace([np.inf, -np.inf], np.nan).ffill()
    return clean.fillna(0.0).astype(float).tolist()


def _helper_globals() -> dict[str, Any]:
    return {
        "close": close,
        "high": high,
        "low": low,
        "volume": volume,
        "latest": latest,
        "previous": previous,
        "sma": sma,
        "ema": ema,
        "rsi": rsi,
        "stdev": stdev,
        "zscore": zscore,
        "pct_change": pct_change,
        "momentum": momentum,
        "highest": highest,
        "lowest": lowest,
        "crosses_above": crosses_above,
        "crosses_below": crosses_below,
        "top_n": top_n,
        "bottom_n": bottom_n,
        "clamp": clamp,
    }


def _coerce_series(values: Any) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        return np.asarray([float(array)], dtype=float)
    return np.nan_to_num(array.astype(float), nan=0.0, posinf=0.0, neginf=0.0)


def _field(data: dict[str, dict[str, list[float]]], ticker: str, key: str) -> np.ndarray:
    if ticker not in data:
        raise CustomStrategyValidationError(f"{ticker} is not in the current universe.")
    return _coerce_series(data[ticker].get(key, []))


def close(data: dict[str, dict[str, list[float]]], ticker: str) -> np.ndarray:
    return _field(data, ticker, "adj_close")


def high(data: dict[str, dict[str, list[float]]], ticker: str) -> np.ndarray:
    return _field(data, ticker, "high")


def low(data: dict[str, dict[str, list[float]]], ticker: str) -> np.ndarray:
    return _field(data, ticker, "low")


def volume(data: dict[str, dict[str, list[float]]], ticker: str) -> np.ndarray:
    return _field(data, ticker, "volume")


def latest(values: Any, default: float = 0.0) -> float:
    series = _coerce_series(values)
    if len(series) == 0:
        return float(default)
    return float(series[-1])


def previous(values: Any, default: float = 0.0) -> float:
    series = _coerce_series(values)
    if len(series) < 2:
        return float(default)
    return float(series[-2])


def sma(values: Any, window: int) -> np.ndarray:
    series = pd.Series(_coerce_series(values))
    return series.rolling(int(window), min_periods=1).mean().to_numpy(dtype=float)


def ema(values: Any, window: int) -> np.ndarray:
    series = pd.Series(_coerce_series(values))
    return series.ewm(span=max(int(window), 1), adjust=False).mean().to_numpy(dtype=float)


def rsi(values: Any, window: int = 14) -> np.ndarray:
    series = pd.Series(_coerce_series(values))
    delta = series.diff().fillna(0.0)
    gain = delta.clip(lower=0.0).rolling(window, min_periods=1).mean()
    loss = (-delta.clip(upper=0.0)).rolling(window, min_periods=1).mean()
    rs = gain / loss.replace(0.0, np.nan)
    result = 100 - (100 / (1 + rs))
    return result.fillna(50.0).to_numpy(dtype=float)


def stdev(values: Any, window: int) -> np.ndarray:
    series = pd.Series(_coerce_series(values))
    return series.rolling(int(window), min_periods=1).std().fillna(0.0).to_numpy(dtype=float)


def zscore(values: Any, window: int) -> np.ndarray:
    series = pd.Series(_coerce_series(values))
    mean = series.rolling(int(window), min_periods=1).mean()
    sigma = series.rolling(int(window), min_periods=1).std().replace(0.0, np.nan)
    return ((series - mean) / sigma).fillna(0.0).to_numpy(dtype=float)


def pct_change(values: Any, periods: int = 1) -> np.ndarray:
    series = pd.Series(_coerce_series(values))
    return series.pct_change(periods=max(int(periods), 1)).fillna(0.0).to_numpy(dtype=float)


def momentum(values: Any, lookback: int) -> float:
    series = _coerce_series(values)
    lookback = int(lookback)
    if len(series) <= lookback or lookback <= 0:
        return 0.0
    start_value = float(series[-lookback - 1])
    end_value = float(series[-1])
    if abs(start_value) <= 1e-12:
        return 0.0
    return (end_value / start_value) - 1


def highest(values: Any, window: int) -> float:
    series = _coerce_series(values)
    if len(series) == 0:
        return 0.0
    window = max(int(window), 1)
    return float(np.max(series[-window:]))


def lowest(values: Any, window: int) -> float:
    series = _coerce_series(values)
    if len(series) == 0:
        return 0.0
    window = max(int(window), 1)
    return float(np.min(series[-window:]))


def crosses_above(left: Any, right: Any) -> bool:
    left_series = _coerce_series(left)
    right_series = _coerce_series(right)
    if len(left_series) < 2 or len(right_series) < 2:
        return False
    return bool(left_series[-1] > right_series[-1] and left_series[-2] <= right_series[-2])


def crosses_below(left: Any, right: Any) -> bool:
    left_series = _coerce_series(left)
    right_series = _coerce_series(right)
    if len(left_series) < 2 or len(right_series) < 2:
        return False
    return bool(left_series[-1] < right_series[-1] and left_series[-2] >= right_series[-2])


def top_n(scores: dict[str, float], n: int) -> list[str]:
    return [
        ticker
        for ticker, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)[: int(n)]
    ]


def bottom_n(scores: dict[str, float], n: int) -> list[str]:
    return [ticker for ticker, _ in sorted(scores.items(), key=lambda item: item[1])[: int(n)]]


def clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(upper, value)))
