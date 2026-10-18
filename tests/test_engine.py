import numpy as np
import pytest
from src.engine import entry_signal, exit_reason, leg_quantities, run_backtest
# Вход: z > 2 → -1, z < -2 → +1, иначе 0, NaN → 0
def test_entry_signal():
    assert entry_signal(2.5) == -1      # ETH дорогой → шорт спреда
    assert entry_signal(-2.5) == 1     # ETH дешёвый → лонг спреда
    assert entry_signal(1.0) == 0      # норма → ничего
    assert entry_signal(np.nan) == 0   # первые 287 свечей → ничего


# Выход: по норме, по стопу, по времени, держим
def test_exit_reason():
    assert exit_reason(-1, -0.1, 10) == "mean"   # шорт, z прошёл 0
    assert exit_reason(1, 0.2, 10) == "mean"     # лонг, z прошёл 0
    assert exit_reason(-1, 4.5, 10) == "stop"    # шорт, z ушёл за 4
    assert exit_reason(-1, 1.5, 576) == "time"   # держим уже 2 дня
    assert exit_reason(-1, 1.5, 10) is None      # ничего не сработало

# Границы: > против >=
def test_boundaries():
    assert entry_signal(2.0) == 0                 # ровно 2 — ещё не вход
    assert exit_reason(-1, 0.0, 50) == "mean"     # ровно 0 — уже выход
    assert exit_reason(1, -1.0, 575) is None      # 575 — ещё держим
    assert exit_reason(1, -1.0, 576) == "time"    # 576 — тайм-стоп

def test_leg_quantities():
    qa, qb = leg_quantities(-1, 2500.0, 62500.0)
    assert qa == pytest.approx(-4)
    assert qb == pytest.approx(0.16)

    qa, qb = leg_quantities(1, 2500.0, 62500.0)
    assert qa == pytest.approx(4)
    assert qb == pytest.approx(-0.16)


def test_leg_pnl_sign():
    qa, qb = leg_quantities(-1, 2500.0, 62500.0)
    assert qa * (2450.0 - 2500.0) == pytest.approx(200)

def make_case():
    """6 свечей: одна шорт-сделка, вход на t=2, выход на t=5."""
    z        = np.array([1.0, 2.5, 1.5, 0.5, -0.1, -0.5])
    open_a   = np.array([2500, 2500, 2500, 2480, 2460, 2450], dtype=float)
    close_a  = np.array([2500, 2500, 2490, 2470, 2455, 2450], dtype=float)
    open_b   = np.full(6, 62500.0)
    close_b  = np.full(6, 62500.0)
    tradable = np.full(6, True)
    return open_a, open_b, close_a, close_b, tradable, z


# Одна сделка: каждый доллар посчитан руками
def test_run_backtest_one_trade():
    res = run_backtest(*make_case(), "regular")
    trades = res["trades"]

    assert len(trades) == 1
    t = trades[0]
    assert t["entry_t"] == 2
    assert t["exit_t"] == 5
    assert t["direction"] == -1
    assert t["reason"] == "mean"
    assert t["pnl"] == pytest.approx(176.12)

    np.testing.assert_allclose(res["equity"], [20000, 20000, 20028, 20108, 20168, 20176.12])
    np.testing.assert_allclose(res["qty_a"], [0, 0, -4, -4, -4, 0])


# Биржа стояла на t=2 → вход переносится на t=3
def test_run_backtest_halt_delays_entry():
    open_a, open_b, close_a, close_b, tradable, z = make_case()
    tradable[2] = False
    res = run_backtest(open_a, open_b, close_a, close_b, tradable, z, "regular")
    assert res["trades"][0]["entry_t"] == 3



# z не вернулся к 0 → сделка закрывается в конце данных с причиной "end"
def test_run_backtest_closes_at_end():
    open_a, open_b, close_a, close_b, tradable, _ = make_case()
    z = np.array([1.0, 2.5, 1.5, 1.2, 1.0, 0.8])     # после входа z не доходит до 0
    res = run_backtest(open_a, open_b, close_a, close_b, tradable, z, "regular")

    t = res["trades"][0]
    assert t["entry_t"] == 2
    assert t["exit_t"] == 5
    assert t["reason"] == "end"
    assert t["pnl"] == pytest.approx(176.12)
    assert res["equity"][-1] == pytest.approx(20176.12)