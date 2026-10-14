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


def check_bars(df: pl.DataFrame, step_ms: int) -> dict:
    """Проверка качества: дубли, пропуски, некорректные свечи, минуты без торговли."""
    n_rows = df.height
    n_duplicates = n_rows - df["open_time"].n_unique()

    gaps = df.filter(pl.col("open_time").diff() > step_ms)

    bad_ohlc = df.filter(
        (pl.col("high") < pl.max_horizontal("open", "close"))
        | (pl.col("low") > pl.min_horizontal("open", "close"))
    )

    zero_volume = df.filter(pl.col("volume") == 0)          # новое

    return {
        "n_rows": n_rows,
        "n_duplicates": n_duplicates,
        "gaps": gaps.height,
        "bad_ohlc": bad_ohlc.height,
        "zero_volume": zero_volume.height,                  # новое
    }

def align_pair(a: pl.DataFrame, b: pl.DataFrame) -> pl.DataFrame:
    """Соединить две монеты по open_time: столбцы A с суффиксом _a, B с суффиксом _b."""
    a = a.rename({c: f"{c}_a" for c in a.columns if c != "open_time"})
    b = b.rename({c: f"{c}_b" for c in b.columns if c != "open_time"})
    return a.join(b, on="open_time", how="inner").sort("open_time")

def resample(df: pl.DataFrame, step_ms: int) -> pl.DataFrame:
    """Свечи 1m одной монеты -> свечи крупнее (например, 5m = 300_000 мс)."""
    return (
        df.with_columns((pl.col("open_time") // step_ms * step_ms).alias("bucket"))
        .group_by("bucket", maintain_order=True)
        .agg(
            pl.col("open").first(),
            pl.col("high").max(),
            pl.col("low").min(),
            pl.col("close").last(),
            pl.col("volume").sum(),
            pl.len().alias("n_bars"),
        )
        .rename({"bucket": "open_time"})
        .sort("open_time")
    )
