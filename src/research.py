import config
from src.signals import log_spread, rolling_zscore
from src.engine_numba import run_backtest_fast
from src.metrics import summary


def evaluate(df, fa, fb, end,
             window: int = config.WINDOW,
             entry_z: float = config.ENTRY_Z,
             stop_z: float = config.STOP_Z,
             max_hold: int = config.MAX_HOLD_BARS,
             max_loss: float = 0.0,                 # NEW: стоп по убытку в $ (0 = выкл)
             max_loss_pct: float = 0.0,             # NEW: стоп по убытку в % капитала (0 = выкл)
             tier: str = "vip7") -> dict:
    """Один прогон стратегии на свечах [0, end) → словарь метрик + параметры."""
    open_a = df["open_a"].to_numpy()
    open_b = df["open_b"].to_numpy()
    close_a = df["close_a"].to_numpy()
    close_b = df["close_b"].to_numpy()
    tradable = ((df["n_traded_a"] > 0) & (df["n_traded_b"] > 0)).to_numpy()   # обе монеты торговались

    # z считаем на ВСЕХ данных, потом режем (rolling смотрит только назад → утечки нет)
    z = rolling_zscore(log_spread(close_a, close_b), window)

    cut = slice(0, end)                                   # только год 1
    res = run_backtest_fast(
        open_a[cut], open_b[cut], close_a[cut], close_b[cut], tradable[cut], z[cut],
        tier, fa[cut], fb[cut],
        entry_z=entry_z, stop_z=stop_z, max_hold=max_hold,
        max_loss=max_loss, max_loss_pct=max_loss_pct)     # NEW

    out = summary(res)
    out.update({"window": window, "entry_z": entry_z, "stop_z": stop_z,
                "max_hold": max_hold, "max_loss": max_loss,
                "max_loss_pct": max_loss_pct, "tier": tier})     # NEW: записываем в журнал
    return out