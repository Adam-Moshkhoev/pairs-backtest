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
    """Свечи 1m -> крупнее. open/high/low только по минутам с торговлей."""
    traded = pl.col("volume") > 0

    return (
        df.with_columns((pl.col("open_time") // step_ms * step_ms).alias("bucket"))
        .group_by("bucket", maintain_order=True)
        .agg(
            pl.col("open").filter(traded).first().fill_null(pl.col("open").first()),
            pl.col("high").filter(traded).max().fill_null(pl.col("high").max()),
            pl.col("low").filter(traded).min().fill_null(pl.col("low").min()),
            pl.col("close").last(),
            pl.col("volume").sum(),
            pl.len().alias("n_bars"),
            traded.sum().alias("n_traded"),
        )
        .rename({"bucket": "open_time"})
        .sort("open_time")
    )

def build_dataset() -> None:
    """Zip-файлы -> проверенные и соединённые пары 1m и 5m в data/processed."""
    step_1m, step_5m = config.STEP_MS["1m"], config.STEP_MS["5m"]

    # 1. Загрузка
    a = load_klines(config.SYMBOL_A)
    b = load_klines(config.SYMBOL_B)

    # 2. Проверка
    print(config.SYMBOL_A, check_bars(a, step_1m))
    print(config.SYMBOL_B, check_bars(b, step_1m))

    # 3. Флаг торговли для минуток
    a = a.with_columns((pl.col("volume") > 0).cast(pl.UInt32).alias("n_traded"))
    b = b.with_columns((pl.col("volume") > 0).cast(pl.UInt32).alias("n_traded"))

    # 4–5. Пары
    pair_1m = align_pair(a, b)
    pair_5m = align_pair(resample(a, step_5m), resample(b, step_5m))

    # 6. Сохранение
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pair_1m.write_parquet(config.PROCESSED_DIR / "pair_1m.parquet")
    pair_5m.write_parquet(config.PROCESSED_DIR / "pair_5m.parquet")
    print("1m:", pair_1m.shape, "| 5m:", pair_5m.shape)


if __name__ == "__main__":
    build_dataset()