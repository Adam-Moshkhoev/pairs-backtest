import numpy as np
import polars as pl
import config


def positions_frame(open_time, qty_a, qty_b, close_a, close_b) -> pl.DataFrame:
    """Позиции в формате команды: symbol, timestamp, position_qty, close_price (2 строки на свечу)."""
    ts = pl.from_epoch(pl.Series(open_time), time_unit="ms")      # миллисекунды → дата

    eth = pl.DataFrame({"timestamp": ts, "position_qty": qty_a, "close_price": close_a}) \
            .with_columns(pl.lit(config.SYMBOL_A).alias("symbol"))   # ETHUSDT
    btc = pl.DataFrame({"timestamp": ts, "position_qty": qty_b, "close_price": close_b}) \
            .with_columns(pl.lit(config.SYMBOL_B).alias("symbol"))   # BTCUSDT

    return (
        pl.concat([eth, btc])                                     # склеили ETH и BTC
        .sort(["timestamp", "symbol"])                            # по времени, на каждой свече обе ноги рядом
        .select("symbol", "timestamp", "position_qty", "close_price")   # порядок колонок как просила команда
    )


def save_positions(frame: pl.DataFrame, name: str) -> None:
    """Сохранить таблицу позиций в reports/<name>.parquet."""
    path = config.ROOT / "reports" / f"{name}.parquet"
    frame.write_parquet(path)