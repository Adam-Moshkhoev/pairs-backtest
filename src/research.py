import numpy as np
import polars as pl
import config
from src.signals import log_spread, rolling_zscore
from src.engine_numba import run_backtest_fast
from src.metrics import summary


def evaluate(df: pl.DataFrame, fa: np.ndarray, fb: np.ndarray, end: int,
             window: int = config.WINDOW, entry_z: float = config.ENTRY_Z,
             stop_z: float = config.STOP_Z, max_hold: int = config.MAX_HOLD_BARS,
             tier: str = "vip7") -> dict:
    """Прогнать одну настройку на свечах [0:end] (год 1) и вернуть метрики."""
    z = rolling_zscore(log_spread(df["close_a"].to_numpy(), df["close_b"].to_numpy()), window)   # z по всем данным
    tradable = ((df["n_traded_a"] > 0) & (df["n_traded_b"] > 0)).to_numpy()

    cut = slice(0, end)                                       # только год 1
    res = run_backtest_fast(
        df["open_a"].to_numpy()[cut], df["open_b"].to_numpy()[cut],
        df["close_a"].to_numpy()[cut], df["close_b"].to_numpy()[cut],
        tradable[cut], z[cut], tier, fa[cut], fb[cut],
        entry_z=entry_z, stop_z=stop_z, max_hold=max_hold,
    )
    out = summary(res)                                        # все метрики одним словарём
    out.update({"window": window, "entry_z": entry_z, "stop_z": stop_z,
                "max_hold": max_hold, "tier": tier})          # подписали параметры
    return out