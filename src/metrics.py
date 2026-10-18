import numpy as np
import config

BARS_PER_DAY = 288          # 5-минутных свечей в сутках
DAYS_PER_YEAR = 365         # крипта торгуется каждый день


def total_return(equity: np.ndarray) -> float:
    """Доходность за весь период: капитал в конце / в начале − 1."""
    return equity[-1] / config.CAPITAL - 1              # 22 000 / 20 000 − 1 = 0.10 → +10%


def max_drawdown(equity: np.ndarray) -> float:
    """Самое глубокое падение от пика (отрицательное число, −0.25 = −25%)."""
    peak = np.maximum.accumulate(equity)                # лучший капитал до сих пор на каждой свече
    dd = equity / peak - 1                              # насколько ниже пика сейчас
    return dd.min()                                     # самое глубокое падение


def daily_returns(equity: np.ndarray) -> np.ndarray:
    """Дневные доходности: капитал в конце каждого дня → изменение в %."""
    eod = equity[BARS_PER_DAY - 1 :: BARS_PER_DAY]      # каждая 288-я свеча = конец дня
    eod = np.concatenate([[config.CAPITAL], eod])       # в начало — стартовый капитал
    return eod[1:] / eod[:-1] - 1                       # сегодня / вчера − 1


def sharpe(daily_ret: np.ndarray) -> float:
    """Годовой Sharpe: среднее / отклонение дневных доходностей × √365."""
    return daily_ret.mean() / daily_ret.std(ddof=1) * np.sqrt(DAYS_PER_YEAR)   # прибыль на единицу риска


def trade_stats(trades: list[dict]) -> dict:
    """Статистика сделок: число, % прибыльных, средняя, средняя прибыль/убыток, profit factor."""
    pnl = np.array([t["pnl"] for t in trades])          # прибыль каждой сделки
    wins = pnl[pnl > 0]                                 # только прибыльные
    losses = pnl[pnl < 0]                               # только убыточные
    return {
        "n_trades": len(pnl),                           # сколько сделок
        "win_rate": len(wins) / len(pnl),               # доля прибыльных
        "avg_trade": pnl.mean(),                        # средняя сделка
        "avg_win": wins.mean(),                         # средний выигрыш
        "avg_loss": losses.mean(),                      # средний проигрыш (отрицательный)
        "profit_factor": wins.sum() / abs(losses.sum()),  # все выигрыши / все проигрыши; > 1 → в плюсе
    }


def exposure(qty_a: np.ndarray) -> float:
    """Доля свечей, когда мы в позиции."""
    return np.mean(qty_a != 0)                          # в позиции = монет не ноль (лонг или шорт)


def summary(res: dict) -> dict:
    """Все метрики одним словарём."""
    eq = res["equity"]
    out = {
        "total_return": total_return(eq),
        "max_drawdown": max_drawdown(eq),
        "sharpe": sharpe(daily_returns(eq)),
        "exposure": exposure(res["qty_a"]),
    }
    out.update(trade_stats(res["trades"]))              # добавили статистику сделок
    return out