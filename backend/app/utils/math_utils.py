import numpy as np


TRADING_DAYS_PER_YEAR = 252


def annualize_return(daily_return: float) -> float:
    """Annualize a daily return."""
    return (1 + daily_return) ** TRADING_DAYS_PER_YEAR - 1


def annualize_volatility(daily_std: float) -> float:
    """Annualize daily standard deviation."""
    return daily_std * np.sqrt(TRADING_DAYS_PER_YEAR)
