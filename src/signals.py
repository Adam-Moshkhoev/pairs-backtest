import numpy as np
import polars as pl

def log_spread(close_a: np.ndarray, close_b: np.ndarray, beta: float = 1.0) -> np.ndarray:
    """Логарифмическая спредовая стратегия: log(close_a) - beta * log(close_b)."""
    return np.log(close_a) - beta * np.log(close_b)

def rolling_zscore(spread:np.ndarray, window:int)->np.ndarray:
    """Z-score спреда по скользящему окну."""
    s = pl.Series(spread)
    mean = s.rolling_mean(window).to_numpy()
    std = s.rolling_std(window).to_numpy()
    return (spread - mean) / std