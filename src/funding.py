import io
import zipfile

import numpy as np
import polars as pl
import config


def round_to_bar(ms, step: int):
    """Округлить время (мс) до ближайшей свечи шагом step."""
    return (ms + step // 2) // step * step                 # +половина шага → округление к ближайшей


def read_funding_zip(path) -> pl.DataFrame:
    """Один месячный zip → таблица calc_time, last_funding_rate."""
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])                       # CSV внутри zip
    return pl.read_csv(io.BytesIO(raw)).select("calc_time", "last_funding_rate")


def load_funding(symbol: str) -> pl.DataFrame:
    """Все месяцы фандинга → funding_time (округлено до 5m), rate."""
    folder = config.RAW_DIR / "funding" / symbol
    paths = sorted(folder.glob(f"{symbol}-fundingRate-*.zip"))
    df = pl.concat([read_funding_zip(p) for p in paths])   # все месяцы в одну таблицу
    step = config.STEP_MS["5m"]
    return (
        df.with_columns(round_to_bar(pl.col("calc_time"), step).alias("funding_time"))
          .select("funding_time", pl.col("last_funding_rate").alias("rate"))   # переименовали один раз
          .sort("funding_time")
    )


def funding_on_bars(open_time: np.ndarray, funding: pl.DataFrame) -> np.ndarray:
    """Ставка фандинга на каждой свече: на свече выплаты — ставка, иначе 0."""
    bars = pl.DataFrame({"open_time": open_time})          # все свечи
    f = funding.rename({"funding_time": "open_time"})       # одинаковое имя для join
    joined = bars.join(f, on="open_time", how="left")       # все свечи + ставка там, где была выплата
    return joined["rate"].fill_null(0).to_numpy()           # нет выплаты → 0