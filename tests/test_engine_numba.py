import numpy as np
import pytest
from src.engine import run_backtest
from src.engine_numba import run_backtest_fast
from tests.test_engine import make_case


def _same(a, b):
    """Результаты двух движков совпадают: капитал, позиции, сделки."""
    np.testing.assert_allclose(a["equity"], b["equity"])          # капитал на каждой свече
    np.testing.assert_allclose(a["qty_a"], b["qty_a"])            # позиция ETH на каждой свече
    np.testing.assert_allclose(a["qty_b"], b["qty_b"])            # позиция BTC на каждой свече
    assert len(a["trades"]) == len(b["trades"])                   # одинаковое число сделок
    for ta, tb in zip(a["trades"], b["trades"]):                  # каждая сделка по отдельности
        assert (ta["entry_t"], ta["exit_t"], ta["direction"], ta["reason"]) == \
               (tb["entry_t"], tb["exit_t"], tb["direction"], tb["reason"])
        assert ta["pnl"] == pytest.approx(tb["pnl"])
        assert ta["funding"] == pytest.approx(tb["funding"])


# Ручной сценарий из тестов движка: одна шорт-сделка
def test_fast_equals_python_small():
    args = make_case()
    _same(run_backtest(*args, "regular"), run_backtest_fast(*args, "regular"))


# Случайные цены: много сделок, стопы, тайм-стопы, остановки биржи, фандинг
def test_fast_equals_python_random():
    rng = np.random.default_rng(0)                                # одинаковые данные каждый раз
    n = 5000
    close_a = 2500 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))   # случайное блуждание цены ETH
    close_b = 62500 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))  # и BTC
    open_a, open_b = close_a * 0.999, close_b * 1.001             # open чуть отличается от close
    tradable = rng.random(n) > 0.01                               # ~1% свечей «биржа стояла»
    z = rng.normal(0, 1.5, n)                                     # случайный z
    z[:50] = np.nan                                               # NaN в начале, как в реальности
    fa = np.where(np.arange(n) % 96 == 0, 0.0001, 0.0)            # выплата раз в 96 свечей (8 ч)
    fb = np.where(np.arange(n) % 96 == 0, -0.0001, 0.0)
    args = (open_a, open_b, close_a, close_b, tradable, z)
    _same(run_backtest(*args, "vip7", fa, fb), run_backtest_fast(*args, "vip7", fa, fb))


# Сделка открыта в конце данных → причина "end" (проверка кода 4)
def test_fast_end_of_data():
    open_a, open_b, close_a, close_b, tradable, _ = make_case()
    z = np.array([1.0, 2.5, 1.5, 1.2, 1.0, 0.8])                  # z не возвращается к 0
    args = (open_a, open_b, close_a, close_b, tradable, z)
    a = run_backtest(*args, "regular")
    b = run_backtest_fast(*args, "regular")
    _same(a, b)
    assert b["trades"][0]["reason"] == "end"