from datetime import date, timedelta

import pandas as pd


def trading_days_between(start: date, end: date) -> list[date]:
    """Return business days between start and end (inclusive)."""
    bdays = pd.bdate_range(start, end)
    return [d.date() for d in bdays]


def years_between(start: date, end: date) -> float:
    """Return the number of years between two dates."""
    delta = end - start
    return delta.days / 365.25
