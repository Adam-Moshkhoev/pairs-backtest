"""Тесты подготовки данных: готовый pair_5m.parquet и функция resample.

Запуск: python -m pytest -q
"""

import polars as pl
import pytest

from src.prepare import resample
import config

STEP_5M = config.STEP_MS["5m"]   # 5 минут в мс
MIN = config.STEP_MS["1m"]       # 1 минута в мс


@pytest.fixture(scope="module")
def pair_5m():
    """Готовые 5m-данные; читаются один раз на весь файл."""
    return pl.read_parquet(config.PROCESSED_DIR / "pair_5m.parquet")


# ---------- Проверка готовых данных ----------

def test_5m_time_step(pair_5m):
    """Между соседними свечами ровно 5 минут: нет пропусков."""
    diffs = pair_5m["open_time"].diff().drop_nulls()
    assert (diffs == STEP_5M).all()


def test_5m_no_duplicates(pair_5m):
    """Каждое время встречается один раз."""
    assert pair_5m['open_time'].n_unique() == pair_5m.height


def test_5m_ohlc_valid(pair_5m):
    """Нет невозможных свечей: high >= open/close, low <= open/close (обе ноги)."""
    for leg in ["a","b"]:
        o, h, l, c = f"open_{leg}", f"high_{leg}", f"low_{leg}", f"close_{leg}"
        bad = pair_5m.filter(
            (pl.col(h) < pl.max_horizontal(o, c))
            | (pl.col(l) > pl.min_horizontal(o, c))
        )
        assert bad.height == 0


# ---------- resample на маленьком примере ----------

def test_resample_basic():
    """10 минуток -> 2 пятиминутки с известными заранее значениями."""
    df = pl.DataFrame({
        "open_time": [i * MIN for i in range(10)],
        "open":   [100, 101, 104, 103,  99, 100, 102, 106, 105, 104],
        "high":   [102, 105, 104, 103, 101, 103, 107, 106, 105, 106],
        "low":    [ 99, 100, 102,  98,  99, 100, 101, 104, 103, 104],
        "close":  [101, 104, 103,  99, 100, 102, 106, 105, 104, 105],
        "volume": [ 10,  20,  15,  30,  25,  10,  40,  20,  15,   5],
    }).cast({"open": pl.Float64, "high": pl.Float64, "low": pl.Float64,
             "close": pl.Float64, "volume": pl.Float64})

    out = resample(df, STEP_5M)

    assert out.height == 2
    assert out["open"].to_list()   == [100, 100]   # первый
    assert out["high"].to_list()   == [105, 107]   # максимум
    assert out["low"].to_list()    == [98, 100]    # минимум
    assert out["close"].to_list()  == [100, 105]   # последний
    assert out["volume"].to_list() == [100, 90]    # сумма


def test_resample_ignores_no_trade_minutes():
    """4 минуты без торговли (цена 90) не должны попасть в open и low."""
    df = pl.DataFrame({
        "open_time": [i * MIN for i in range(5)],
        "open":   [90, 90, 90, 90, 100],
        "high":   [90, 90, 90, 90, 101],
        "low":    [90, 90, 90, 90,  99],
        "close":  [90, 90, 90, 90, 100],
        "volume": [ 0,  0,  0,  0,  50],
    }).cast({"open": pl.Float64, "high": pl.Float64, "low": pl.Float64,
             "close": pl.Float64, "volume": pl.Float64})

    out = resample(df, STEP_5M)

    assert out["open"][0] == 100     # open первой минуты с торговлей
    assert out["low"][0] == 99       # минимум только по минутам с торговлей
    assert out["n_traded"][0] == 1   # торговля была в 1 минуте из 5