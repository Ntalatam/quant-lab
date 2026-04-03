from pydantic import BaseModel, ConfigDict, Field


class LoadDataRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
            }
        }
    )

    ticker: str = Field(description="Ticker symbol to fetch and cache.")
    start_date: str = Field(description="Inclusive ISO start date.")
    end_date: str = Field(description="Inclusive ISO end date.")


class LoadDataResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "ticker": "AAPL",
            }
        }
    )

    status: str
    ticker: str


class OHLCVPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticker": "AAPL",
                "original_rows": 1250,
                "returned_rows": 500,
                "data": [
                    {
                        "date": "2024-01-02",
                        "open": 187.12,
                        "high": 188.44,
                        "low": 186.51,
                        "close": 187.92,
                        "volume": 53421000,
                    }
                ],
            }
        }
    )

    ticker: str
    original_rows: int
    returned_rows: int
    data: list[OHLCVPoint]
