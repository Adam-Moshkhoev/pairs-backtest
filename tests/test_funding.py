import numpy as np
import polars as pl
import config
from src.funding import round_to_bar, funding_on_bars

STEP = config.STEP_MS["5m"]


# +1 мс и −1 мс округляются к одной и той же свече
def test_round_to_bar():
    t = 1727798400000                                   # 2024-10-01 16:00:00
    assert round_to_bar(t + 1, STEP) == t
    assert round_to_bar(t - 1, STEP) == t
    assert round_to_bar(t, STEP) == t


# 3 свечи, выплата на второй → [0, ставка, 0]
def test_funding_on_bars():
    open_time = np.array([0, STEP, 2 * STEP])
    funding = pl.DataFrame({"funding_time": [STEP], "rate": [0.0001]})
    np.testing.assert_allclose(funding_on_bars(open_time, funding), [0, 0.0001, 0])