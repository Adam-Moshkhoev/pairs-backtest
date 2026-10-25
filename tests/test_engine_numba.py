import numpy as np
import pytest

import config
from src.engine import run_backtest
from src.engine_numba import run_backtest_fast
from src.signals import log_spread, rolling_zscore
from tests.test_engine import make_case


def _same(a, b):
    """Два результата бэктеста совпадают: equity, позиции и все сделки."""
    assert np.allclose(a["equity"], b["equity"])
    assert np.allclose(a["qty_a"], b["qty_a"])
    assert np.allclose(a["qty_b"], b["qty_b"])
    assert len(a["trades"]) == len(b["trades"])
    for ta, tb in zip(a["trades"], b["trades"]):
        assert ta["entry_t"] == tb["entry_t"]
        assert ta["exit_t"] == tb["exit_t"]
        assert ta["direction"] == tb["direction"]
        assert ta["reason"] == tb["reason"]
        assert ta["pnl"] == pytest.approx(tb["pnl"])
        assert ta["funding"] == pytest.approx(tb["funding"])


# ── Старые тесты: numba = Python ──

# Маленький ручной пример из test_engine
def test_small_case_same_as_python():
    args = make_case()
    _same(run_backtest(*args, "regular"), run_backtest_fast(*args, "regular"))


# 5000 случайных свечей + фандинг → много сделок всех типов
def test_random_same_as_python():
    rng = np.random.default_rng(42)
    n = 5000
    close_a = 2500 * np.exp(np.cumsum(rng.normal(0, 0.003, n)))
    close_b = 62500 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    open_a = np.r_[close_a[0], close_a[:-1]]                # open = прошлый close
    open_b = np.r_[close_b[0], close_b[:-1]]
    tradable = rng.random(n) > 0.01                         # ~1% свечей без торговли
    z = rolling_zscore(log_spread(close_a, close_b), 288)
    fa = np.zeros(n)
    fb = np.zeros(n)
    fa[::96] = 0.0001                                       # фандинг каждые 8 ч
    fb[::96] = -0.00005

    py = run_backtest(open_a, open_b, close_a, close_b, tradable, z, "vip7", fa, fb)
    nb = run_backtest_fast(open_a, open_b, close_a, close_b, tradable, z, "vip7", fa, fb)
    _same(py, nb)


# Позиция открыта в конце данных → закрываем по последнему close, причина "end"
def test_end_of_data_same_as_python():
    n = 20
    close_a = 2500.0 + np.arange(n)
    close_b = np.full(n, 62500.0)
    tradable = np.ones(n, dtype=bool)
    z = np.full(n, 3.0)                                     # вход и до конца без выхода

    py = run_backtest(close_a, close_b, close_a, close_b, tradable, z, "regular")
    nb = run_backtest_fast(close_a, close_b, close_a, close_b, tradable, z, "regular")
    assert nb["trades"][-1]["reason"] == "end"
    _same(py, nb)


# ── Новые тесты: стоп по убытку (4.1) ──

# Стоп по деньгам: шорт, ETH растёт → на t=2 убыток $212 > $150 → выход на open t=3
def test_loss_stop():
    z        = np.array([1.0, 2.5, 2.6, 2.7, 2.8, 2.9])     # z не возвращается к 0
    open_a   = np.array([2500, 2500, 2500, 2560, 2570, 2580], dtype=float)
    close_a  = np.array([2500, 2500, 2550, 2565, 2575, 2580], dtype=float)
    open_b   = np.full(6, 62500.0)
    close_b  = np.full(6, 62500.0)
    tradable = np.full(6, True)
    res = run_backtest_fast(open_a, open_b, close_a, close_b, tradable, z, "regular",
                            max_loss=150.0)
    t = res["trades"][0]
    assert t["reason"] == "loss"
    assert t["exit_t"] == 3
    assert t["pnl"] == pytest.approx(-264.144)              # −240 − 12 − 12.144


# max_loss = 0 → правило выключено, результат как у v1
def test_loss_stop_off_equals_v1():
    args = make_case()
    _same(run_backtest(*args, "regular"), run_backtest_fast(*args, "regular", max_loss=0.0))


# 1% от капитала $20 000 = $200 → та же сделка, что и max_loss=200
def test_loss_pct_same_as_dollars():
    n = 50
    close_a = 2500.0 + 10.0 * np.arange(n)                  # ETH растёт: 2500, 2510, 2520 …
    close_b = np.full(n, 62500.0)                           # BTC стоит
    tradable = np.ones(n, dtype=bool)
    z = np.full(n, 3.0)                                     # z=3: вход в шорт, mean и stop не сработают

    usd = run_backtest_fast(close_a, close_b, close_a, close_b, tradable, z, "vip7",
                            max_loss=200.0)
    pct = run_backtest_fast(close_a, close_b, close_a, close_b, tradable, z, "vip7",
                            max_loss_pct=200.0 / config.CAPITAL)

    assert len(usd["trades"]) == 1                          # после loss пауза → новых входов нет
    assert usd["trades"][0]["reason"] == "loss"             # вышли именно по loss
    assert usd["trades"] == pct["trades"]                   # оба способа дали одинаковую сделку

# beta = все 1 → ровно v1
def test_beta_one_equals_v1():
    args = make_case()
    n = len(args[0])
    _same(run_backtest(*args, "regular"),
          run_backtest_fast(*args, "regular", beta=np.ones(n)))


# β = 1.5 при решении о входе → нога BTC $15 000; β потом меняется, но сделка держит 1.5
def test_beta_leg_size():
    z        = np.array([1.0, 2.5, 2.6, -0.1, 0.0])          # вход t=1 → исполнение t=2; z ≤ 0 на t=3 → выход t=4
    open_a   = np.array([2500, 2500, 2500, 2480, 2450], dtype=float)
    close_a  = open_a.copy()
    open_b   = np.array([62500, 62500, 62500, 62300, 62000], dtype=float)
    close_b  = open_b.copy()
    tradable = np.full(5, True)
    beta     = np.array([1.0, 1.5, 2.0, 2.0, 2.0])           # решение на t=1 → β = 1.5

    res = run_backtest_fast(open_a, open_b, close_a, close_b, tradable, z, "regular", beta=beta)
    t = res["trades"][0]

    assert res["qty_a"][2] == pytest.approx(-4.0)            # шорт ETH: 10 000 / 2 500
    assert res["qty_b"][2] == pytest.approx(0.24)            # лонг BTC: 1.5 × 10 000 / 62 500
    assert t["reason"] == "mean"
    assert t["exit_t"] == 4
    assert t["pnl"] == pytest.approx(50.192)

# exit_z = 0 → ровно v1
def test_exit_z_zero_equals_v1():
    args = make_case()
    _same(run_backtest(*args, "regular"), run_backtest_fast(*args, "regular", exit_z=0.0))


# шорт при z=2.5; z опускается только до 0.4 и 0.3 (до 0 не доходит)
# exit_z = 0.5 → выход по mean на t=4;  exit_z = 0 → сделка висит до конца данных ("end")
def test_exit_z_early_exit():
    z        = np.array([1.0, 2.5, 2.6, 0.4, 0.3])
    open_a   = np.array([2500, 2500, 2500, 2490, 2480], dtype=float)
    close_a  = open_a.copy()
    open_b   = np.full(5, 62500.0)
    close_b  = open_b.copy()
    tradable = np.full(5, True)
    args = (open_a, open_b, close_a, close_b, tradable, z)

    early = run_backtest_fast(*args, "regular", exit_z=0.5)["trades"][0]
    assert early["reason"] == "mean"                       # z = 0.4 ≤ 0.5 на t=3 → выход t=4
    assert early["exit_t"] == 4
    assert early["pnl"] == pytest.approx(56.048)           # +80 − 12 − 11.952

    late = run_backtest_fast(*args, "regular", exit_z=0.0)["trades"][0]
    assert late["reason"] == "end"                         # z до 0 не дошёл → закрыли в конце данных


# trend = False → ровно v1
def test_trend_false_equals_v1():
    args = make_case()
    _same(run_backtest(*args, "regular"), run_backtest_fast(*args, "regular", trend=False))


# тренд: z = 2.5 → ЛОНГ спреда; ETH растёт; z падает до 0.4 ≤ exit_z = 0.5 → выход "fade"
def test_trend_long_and_fade_exit():
    z        = np.array([1.0, 2.5, 2.6, 0.4, 0.3])
    open_a   = np.array([2500, 2500, 2500, 2550, 2600], dtype=float)
    close_a  = open_a.copy()
    open_b   = np.full(5, 62500.0)
    close_b  = open_b.copy()
    tradable = np.full(5, True)

    res = run_backtest_fast(open_a, open_b, close_a, close_b, tradable, z, "regular",
                            exit_z=0.5, trend=True)
    t = res["trades"][0]
    assert res["qty_a"][2] == pytest.approx(4.0)            # лонг ETH: 10 000 / 2 500
    assert res["qty_b"][2] == pytest.approx(-0.16)          # шорт BTC: 10 000 / 62 500
    assert t["direction"] == 1                              # лонг спреда
    assert t["reason"] == "fade"
    assert t["exit_t"] == 4
    assert t["pnl"] == pytest.approx(375.76)                # +400 − 12 − 12.24


# большой |z| закрывает сделку возврата (stop), но НЕ закрывает трендовую
def test_trend_has_no_z_stop():
    z        = np.array([1.0, 2.5, 5.0, 5.0, 5.0])
    prices   = np.full(5, 2500.0)
    btc      = np.full(5, 62500.0)
    tradable = np.full(5, True)
    args = (prices, btc, prices, btc, tradable, z)

    revert = run_backtest_fast(*args, "regular", trend=False)["trades"][0]
    follow = run_backtest_fast(*args, "regular", trend=True)["trades"][0]
    assert revert["reason"] == "stop"                       # возврат: |z| = 5 > 4 → стоп
    assert follow["reason"] == "end"                        # тренд: держим до конца данных