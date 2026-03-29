from pydantic import BaseModel


class LoadDataRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str


class OHLCVPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVResponse(BaseModel):
    ticker: str
    data: list[OHLCVPoint]
