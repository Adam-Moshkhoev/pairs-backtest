import numpy as np
import pytest

from src.signals import log_spread, rolling_zscore


# Спред = ln(ETH) − beta·ln(BTC) на ценах, где ln считается в уме.
# beta=1 → [1, 1], beta=2 → [1, 0]: формула верна и beta работает.
def test_log_spread_manual():
    close_a = np.array([np.exp(1), np.exp(2)])   # ETH: ln = 1, 2
    close_b = np.array([np.exp(0), np.exp(1)])   # BTC: ln = 0, 1
    np.testing.assert_allclose(log_spread(close_a, close_b), np.array([1, 1]))
    np.testing.assert_allclose(log_spread(close_a, close_b, beta=2), np.array([1, 0]))


# Окно 5: первые 4 значения z — NaN (ещё нет 5 свечей истории).
# С номера 4 и до конца — только числа, без пропусков.
def test_rolling_first_nan():
    spread = np.arange(20, dtype=float)
    window = 5
    z = rolling_zscore(spread, window)
    assert np.isnan(z[:window-1]).all()       # первые 4 → все NaN
    assert not np.isnan(z[window-1:]).any()  # остальные → ни одного NaN


# Сравниваем z с ручным расчётом для [1, 2, 6]:
# среднее = 3, std = √7 → z = (6 − 3) / √7 ≈ 1.134
def test_zscore_manual():
    z = rolling_zscore(np.array([1.0, 2.0, 6.0]), window=3)
    assert z[-1] == pytest.approx(3.0 / np.sqrt(7))


# Главный тест: функция не смотрит в будущее.
# Считаем z по 1500 и по 2000 свечам — на первых 1500 должны совпасть.
def test_no_lookahead():
    rng = np.random.default_rng(42)              # зерно 42 → одинаковые данные каждый раз
    spread = rng.normal(size=2000).cumsum()      # случайное блуждание, как настоящий спред
    z_full = rolling_zscore(spread, window=288)        # знает все 2000 свечей
    z_cut = rolling_zscore(spread[:1500], window=288)  # знает только первые 1500
    np.testing.assert_allclose(z_cut, z_full[:1500], equal_nan=True)  # NaN = NaN считаем совпадением