import numpy as np
import pytest

from src.signals import log_spread, rolling_zscore, rolling_beta, hedged_spread, efficiency_ratio

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


# ETH двигается ровно в 1.5 раза сильнее BTC → β = 1.5
def test_rolling_beta_exact():
    rng = np.random.default_rng(0)
    rb = rng.normal(0, 0.01, 500)
    close_b = 60000 * np.exp(np.cumsum(rb))
    close_a = 2500 * np.exp(np.cumsum(1.5 * rb))       # доходность A = 1.5 × доходность B
    beta = rolling_beta(close_a, close_b, 50)
    assert np.isnan(beta[:50]).all()                    # разогрев: первые 50 — NaN
    assert np.allclose(beta[50:], 1.5)


# при β = 1 новый спред = старый спред − константа → тот же z
def test_hedged_spread_beta_one_equals_log_spread():
    rng = np.random.default_rng(1)
    close_a = 2500 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    close_b = 60000 * np.exp(np.cumsum(rng.normal(0, 0.01, 300)))
    new = hedged_spread(close_a, close_b, np.ones(300))
    old = log_spread(close_a, close_b)
    assert np.allclose(new, old - old[0])


# ── Efficiency ratio (индикатор режима для v4) ──

# Спред 0 → 1 → 3 → 2 → 4, окно 2:
# t=2: движение |3−0| = 3, путь 1+2 = 3 → 1.0
# t=3: движение |2−1| = 1, путь 2+1 = 3 → 1/3
# t=4: движение |4−3| = 1, путь 1+2 = 3 → 1/3
def test_efficiency_ratio_hand_example():
    er = efficiency_ratio(np.array([0.0, 1.0, 3.0, 2.0, 4.0]), 2)
    assert np.isnan(er[0]) and np.isnan(er[1])          # разогрев: первые 2 — NaN
    np.testing.assert_allclose(er[2:], [1.0, 1 / 3, 1 / 3])


# Движение по прямой → ER = 1 (чистый тренд)
def test_efficiency_ratio_straight_line_is_one():
    er = efficiency_ratio(0.01 * np.arange(20.0), 5)
    assert np.isnan(er[:5]).all()
    np.testing.assert_allclose(er[5:], 1.0)


# Туда-сюда 0, 1, 0, 1 … → чистое движение 0 → ER = 0
def test_efficiency_ratio_zigzag_is_zero():
    er = efficiency_ratio(np.array([0.0, 1.0] * 10), 4)
    np.testing.assert_allclose(er[4:], 0.0)


# Меняем только будущее (с t=200) → ER на прошлых свечах не меняется
def test_efficiency_ratio_no_look_ahead():
    rng = np.random.default_rng(0)
    s = np.cumsum(rng.normal(size=300))
    er = efficiency_ratio(s, 50)
    s_changed = s.copy()
    s_changed[200:] += 10.0
    er_changed = efficiency_ratio(s_changed, 50)
    np.testing.assert_allclose(er[:200], er_changed[:200])