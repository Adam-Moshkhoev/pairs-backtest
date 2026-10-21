import config
from src.signals import log_spread, rolling_zscore, rolling_beta, hedged_spread
from src.engine_numba import run_backtest_fast
from src.metrics import summary


def evaluate(df, fa, fb, end,
             window: int = config.WINDOW,
             entry_z: float = config.ENTRY_Z,
             stop_z: float = config.STOP_Z,
             max_hold: int = config.MAX_HOLD_BARS,
             max_loss: float = 0.0,                 # стоп по убытку в $ (0 = выкл)
             max_loss_pct: float = 0.0,             # стоп по убытку в % капитала (0 = выкл)
             beta_window: int = 0,                  # окно скользящего β (0 = β = 1)
             exit_z: float = 0.0,                   # выход по mean при |z| ≤ exit_z (0 = при z = 0)
             tier: str = "vip7") -> dict:
    """Один прогон стратегии на свечах [0, end) → словарь метрик + параметры.

    Без дополнительных параметров = v1.
    """
    open_a = df["open_a"].to_numpy()
    open_b = df["open_b"].to_numpy()
    close_a = df["close_a"].to_numpy()
    close_b = df["close_b"].to_numpy()
    tradable = ((df["n_traded_a"] > 0) & (df["n_traded_b"] > 0)).to_numpy()   # обе монеты торговались

    # спред и β считаем на ВСЕХ данных (rolling смотрит только назад → утечки нет)
    if beta_window > 0:
        beta = rolling_beta(close_a, close_b, beta_window)    # скользящий β
        spread = hedged_spread(close_a, close_b, beta)        # спред из доходностей
    else:
        beta = None                                           # β = 1
        spread = log_spread(close_a, close_b)

    z = rolling_zscore(spread, window)

    cut = slice(0, end)                                       # только год 1
    res = run_backtest_fast(
        open_a[cut], open_b[cut], close_a[cut], close_b[cut], tradable[cut], z[cut],
        tier, fa[cut], fb[cut],
        entry_z=entry_z, stop_z=stop_z, max_hold=max_hold,
        max_loss=max_loss, max_loss_pct=max_loss_pct,
        beta=None if beta is None else beta[cut],
        exit_z=exit_z)

    out = summary(res)
    out.update({"window": window, "entry_z": entry_z, "stop_z": stop_z,
                "max_hold": max_hold, "max_loss": max_loss,
                "max_loss_pct": max_loss_pct, "beta_window": beta_window,
                "exit_z": exit_z, "tier": tier})              # параметры прогона → в журнал
    return out