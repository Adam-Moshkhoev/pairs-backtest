import numpy as np
import pytest
from src.metrics import total_return, max_drawdown, sharpe, trade_stats


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