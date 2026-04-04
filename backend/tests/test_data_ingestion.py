from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import select

from app.models.price_data import PriceData
from app.services import data_ingestion


def _build_download_frame(
    rows: list[tuple[str, float, float, float, float, float, int]],
    *,
    multi_index: bool = False,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "Open": [row[1] for row in rows],
            "High": [row[2] for row in rows],
            "Low": [row[3] for row in rows],
            "Close": [row[4] for row in rows],
            "Adj Close": [row[5] for row in rows],
            "Volume": [row[6] for row in rows],
        },
        index=pd.to_datetime([row[0] for row in rows]),
    )
    if multi_index:
        frame.columns = pd.MultiIndex.from_product([frame.columns, ["AAPL"]])
    return frame


@pytest.mark.asyncio
async def test_ensure_data_loaded_uses_sqlite_upserts_without_duplicate_rows(db, monkeypatch):
    first_download = _build_download_frame(
        [("2024-01-02", 100.0, 101.0, 99.5, 100.5, 100.4, 1_000_000)]
    )
    second_download = _build_download_frame(
        [
            ("2024-01-02", 101.0, 102.0, 100.0, 101.5, 101.4, 1_250_000),
            ("2024-01-03", 102.0, 103.0, 101.5, 102.5, 102.4, 1_500_000),
        ]
    )
    downloads = iter([first_download, second_download])

    monkeypatch.setattr(
        data_ingestion.yf,
        "download",
        lambda *args, **kwargs: next(downloads),
    )

    loaded_initial = await data_ingestion.ensure_data_loaded(
        db,
        "AAPL",
        date(2024, 1, 2),
        date(2024, 1, 2),
    )
    loaded_extended = await data_ingestion.ensure_data_loaded(
        db,
        "AAPL",
        date(2024, 1, 2),
        date(2024, 1, 3),
    )

    rows = (
        (
            await db.execute(
                select(PriceData).where(PriceData.ticker == "AAPL").order_by(PriceData.date)
            )
        )
        .scalars()
        .all()
    )

    assert loaded_initial is True
    assert loaded_extended is True
    assert len(rows) == 2
    assert rows[0].date.isoformat() == "2024-01-02"
    assert rows[0].close == 101.5
    assert rows[0].volume == 1_250_000
    assert rows[1].date.isoformat() == "2024-01-03"


@pytest.mark.asyncio
async def test_ensure_data_loaded_flattens_yfinance_multiindex_columns(db, monkeypatch):
    download_frame = _build_download_frame(
        [
            ("2024-02-01", 190.0, 195.0, 188.0, 193.5, 193.1, 1_800_000),
            ("2024-02-02", 194.0, 196.0, 192.0, 195.5, 195.0, 1_900_000),
        ],
        multi_index=True,
    )
    monkeypatch.setattr(
        data_ingestion.yf,
        "download",
        lambda *args, **kwargs: download_frame,
    )

    loaded = await data_ingestion.ensure_data_loaded(
        db,
        "AAPL",
        date(2024, 2, 1),
        date(2024, 2, 2),
    )
    frame = await data_ingestion.get_price_dataframe(
        db,
        "AAPL",
        date(2024, 2, 1),
        date(2024, 2, 2),
    )

    assert loaded is True
    assert list(frame.columns) == ["open", "high", "low", "close", "adj_close", "volume"]
    assert frame.index[0].date().isoformat() == "2024-02-01"
    assert frame.iloc[-1]["adj_close"] == 195.0
