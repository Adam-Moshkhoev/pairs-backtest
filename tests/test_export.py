import numpy as np
import config
from src.engine import run_backtest
from src.export import positions_frame
from tests.test_engine import make_case


def test_positions_frame():
    open_a, open_b, close_a, close_b, tradable, z = make_case()
    res = run_backtest(open_a, open_b, close_a, close_b, tradable, z, "regular")
    open_time = np.arange(6) * config.STEP_MS["5m"]               # 6 свечей по 5 минут

    f = positions_frame(open_time, res["qty_a"], res["qty_b"], close_a, close_b)

    assert f.columns == ["symbol", "timestamp", "position_qty", "close_price"]
    assert f.height == 12                                        # 6 свечей × 2 монеты
    eth = f.filter(f["symbol"] == config.SYMBOL_A)
    btc = f.filter(f["symbol"] == config.SYMBOL_B)
    np.testing.assert_allclose(eth["position_qty"], [0, 0, -4, -4, -4, 0])
    np.testing.assert_allclose(btc["position_qty"], [0, 0, 0.16, 0.16, 0.16, 0])
    np.testing.assert_allclose(eth["close_price"], close_a)