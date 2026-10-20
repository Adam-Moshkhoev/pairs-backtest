import numpy as np
import pytest
from src.metrics import (total_return, max_drawdown, daily_returns, sharpe,
                         trade_stats, exposure, summary, BARS_PER_DAY)

# 20 000 → 22 000 = +10%
def test_total_return():
    assert total_return(np.array([20000.0, 21000.0, 22000.0])) == pytest.approx(0.1)


# Пример из брифа: пик 120 → дно 90 = −25%
def test_max_drawdown():
    eq = np.array([100.0, 120.0, 90.0, 130.0, 110.0])
    assert max_drawdown(eq) == pytest.approx(-0.25)


# Доходности 1% и 3%: среднее 0.02, std (n−1) = 0.01414 → 1.414 × √365 ≈ 27.02
def test_sharpe():
    ret = np.array([0.01, 0.03])
    assert sharpe(ret) == pytest.approx(27.02, rel=1e-3)


# Сделки +10, +20, −15
def test_trade_stats():
    s = trade_stats([{"pnl": 10.0}, {"pnl": 20.0}, {"pnl": -15.0}])
    assert s["n_trades"] == 3
    assert s["win_rate"] == pytest.approx(2 / 3)
    assert s["avg_win"] == pytest.approx(15.0)
    assert s["avg_loss"] == pytest.approx(-15.0)
    assert s["profit_factor"] == pytest.approx(2.0)

# Крайние случаи: нет сделок / только выигрыши
def test_trade_stats_edge_cases():
    s = trade_stats([])
    assert s["n_trades"] == 0
    assert np.isnan(s["profit_factor"])

    s = trade_stats([{"pnl": 10.0}, {"pnl": 5.0}])
    assert s["avg_loss"] == 0.0
    assert s["profit_factor"] == float("inf")

def test_summary_sharpe_nan_if_bankrupt():
    n = 3 * BARS_PER_DAY                                   # 3 дня свечей
    equity = np.full(n, 20000.0)
    equity[BARS_PER_DAY + 10] = -500.0                     # на 2-й день капитал ушёл в минус
    res = {"equity": equity, "trades": [],
           "qty_a": np.zeros(n), "qty_b": np.zeros(n)}

    out = summary(res)
    assert np.isnan(out["sharpe"])                         # Sharpe недействителен
    assert out["min_equity"] == -500.0                     # минимум виден в таблице