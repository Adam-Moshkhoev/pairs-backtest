import numpy as np
import polars as pl


def log_spread(close_a: np.ndarray, close_b: np.ndarray, beta: float = 1.0) -> np.ndarray:
    """Логарифмический спред: log(close_a) − beta × log(close_b)."""
    return np.log(close_a) - beta * np.log(close_b)


def rolling_zscore(spread: np.ndarray, window: int) -> np.ndarray:
    """Z-score спреда по скользящему окну."""
    s = pl.Series(spread)
    mean = s.rolling_mean(window).to_numpy()
    # mean = s.rolling_mean(window, center=True).to_numpy()  # НЕ ИСПОЛЬЗОВАТЬ: окно по центру смотрит в будущее; только для проверки test_no_lookahead (должен упасть)
    std = s.rolling_std(window).to_numpy()
    return (spread - mean) / std


def rolling_beta(close_a: np.ndarray, close_b: np.ndarray, window: int) -> np.ndarray:
    """Скользящий β по доходностям: на сколько % двигается A при движении B на 1%.

    β = cov(rA, rB) / var(rB) за последние window свечей. Первые window значений — NaN.
    """
    ra = pl.Series(np.diff(np.log(close_a), prepend=np.nan)).fill_nan(None)   # доходность A (первая = пусто)
    rb = pl.Series(np.diff(np.log(close_b), prepend=np.nan)).fill_nan(None)   # доходность B

    mean_a = ra.rolling_mean(window)                 # средняя доходность A за окно
    mean_b = rb.rolling_mean(window)                 # средняя доходность B за окно
    mean_ab = (ra * rb).rolling_mean(window)         # среднее произведения
    mean_bb = (rb * rb).rolling_mean(window)         # среднее квадрата B

    cov = mean_ab - mean_a * mean_b                  # ковариация = E[ab] − E[a]·E[b]
    var = mean_bb - mean_b * mean_b                  # дисперсия  = E[b²] − E[b]²
    return (cov / var).to_numpy()                    # пусто → NaN


def hedged_spread(close_a: np.ndarray, close_b: np.ndarray, beta: np.ndarray) -> np.ndarray:
    """Спред из доходностей: накопленная сумма (rA − β_прошлой_свечи × rB).

    Не прыгает, когда β меняется. При β = 1 совпадает с log_spread с точностью до константы.
    """
    ra = np.diff(np.log(close_a), prepend=np.log(close_a[0]))    # доходность A (первая = 0)
    rb = np.diff(np.log(close_b), prepend=np.log(close_b[0]))    # доходность B (первая = 0)
    beta_prev = np.concatenate([[np.nan], beta[:-1]])            # β, известный на прошлой свече
    r = ra - beta_prev * rb                                      # хеджированная доходность
    r = np.where(np.isnan(r), 0.0, r)                            # пока β не посчитан — 0
    return np.cumsum(r)                                          # накопленная сумма = спред

def efficiency_ratio(spread, lookback):
    """Efficiency ratio спреда за последние `lookback` свечей.

    ER = |s_t − s_(t−lookback)| / сумма |s_i − s_(i−1)| за последние `lookback` шагов.
    1 — движение по прямой (тренд), около 0 — ходит туда-сюда.
    Использует только прошлое; первые `lookback` значений — NaN.
    """
    s = np.asarray(spread, dtype=np.float64)
    step = np.abs(np.diff(s, prepend=np.nan))                              # |s_t − s_(t−1)|, первое значение NaN
    path = pl.Series(step).fill_nan(None).rolling_sum(lookback).to_numpy() # весь путь за последние lookback шагов
    net = np.full(len(s), np.nan)
    net[lookback:] = np.abs(s[lookback:] - s[:-lookback])                  # чистое движение за lookback свечей
    with np.errstate(divide="ignore", invalid="ignore"):
        return net / path