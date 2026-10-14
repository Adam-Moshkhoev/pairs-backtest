import zipfile

from pathlib import Path
import polars as pl

import config

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
    "count", "taker_buy_volume", "taker_quote_volume", "ignore"
]

def read_kline_zip(path:Path)-> pl.DataFrame:
    """Прочитать один zip со свечами -> open_time, open, high, low, close, volume."""
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])

    has_header = not raw[:1].isdigit()

    df = pl.read_csv(raw, has_header = has_header, new_columns = KLINE_COLUMNS)
    return df.select(
        pl.col("open_time").cast(pl.Int64),
        pl.col("open").cast(pl.Float64),
        pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64),
        pl.col("close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64)
    )

def load_klines(symbol:str, interval:str = config.RAW_INTERVAL)-> pl.DataFrame:
    """Все месяцы одной монеты -> одна таблица, отсортированная по времени."""
    folder = config.RAW_DIR/"klines"/symbol
    paths = sorted(folder.glob(f"{symbol}-{interval}-*.zip"))
    df = pl.concat(read_kline_zip(path) for path in paths).sort("open_time")
    return df.sort("open_time")
 