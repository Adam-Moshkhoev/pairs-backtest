"""
Подготовка данных: zip-файлы Binance -> проверенные и соединённые таблицы.

Порядок работы:
    read_kline_zip  — прочитать один zip (один месяц одной монеты)
    load_klines     — склеить все месяцы одной монеты
    check_bars      — проверить качество данных
    align_pair      — соединить две монеты в одну таблицу
    resample        — собрать крупные свечи (5m) из минуток
    build_dataset   — запустить всё по порядку и сохранить parquet

Запуск: python -m src.prepare
"""
import zipfile

from pathlib import Path
import polars as pl

import config

# Все 12 столбцов CSV-файла Binance со свечами, по порядку.
# Нужны, чтобы правильно назвать столбцы, даже если в файле нет заголовка.
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume",
    "count", "taker_buy_volume", "taker_quote_volume", "ignore"
]


def read_kline_zip(path:Path)-> pl.DataFrame:
    """Прочитать один zip со свечами -> open_time, open, high, low, close, volume."""
    # Открываем zip и читаем CSV внутри него (файл там один), не распаковывая на диск
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])

    # Если файл начинается с цифры — это сразу данные, заголовка нет.
    # Если с буквы (open_time,...) — первая строка заголовок.
    has_header = not raw[:1].isdigit()

    # CSV -> таблица; столбцам даём наши имена из KLINE_COLUMNS
    df = pl.read_csv(raw, has_header = has_header, new_columns = KLINE_COLUMNS)

    # Оставляем 6 нужных столбцов из 12 и явно задаём типы:
    # время — целое число (мс), цены и объём — дробные
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
    # Папка с zip-файлами этой монеты, например data/raw/klines/ETHUSDT
    folder = config.RAW_DIR/"klines"/symbol

    # Все zip нужного таймфрейма (без .CHECKSUM); сортировка по имени = по месяцам
    paths = sorted(folder.glob(f"{symbol}-{interval}-*.zip"))

    # Читаем каждый месяц и склеиваем таблицы одна под другой
    df = pl.concat(read_kline_zip(path) for path in paths).sort("open_time")
    return df.sort("open_time")


def check_bars(df: pl.DataFrame, step_ms: int) -> dict:
    """Проверка качества: дубли, пропуски, некорректные свечи, минуты без торговли."""
    n_rows = df.height

    # Дубли: всего строк минус число разных значений времени
    n_duplicates = n_rows - df["open_time"].n_unique()

    # Пропуски: строки, где от предыдущей свечи прошло больше одного шага
    gaps = df.filter(pl.col("open_time").diff() > step_ms)

    # Невозможные свечи: high ниже open/close или low выше open/close
    bad_ohlc = df.filter(
        (pl.col("high") < pl.max_horizontal("open", "close"))
        | (pl.col("low") > pl.min_horizontal("open", "close"))
    )

    # Минуты без торговли (объём 0): цена в них «заморожена» последней сделкой
    zero_volume = df.filter(pl.col("volume") == 0)

    # Отчёт: для чистых данных всё, кроме n_rows и zero_volume, должно быть 0
    return {
        "n_rows": n_rows,
        "n_duplicates": n_duplicates,
        "gaps": gaps.height,
        "bad_ohlc": bad_ohlc.height,
        "zero_volume": zero_volume.height,
    }


def align_pair(a: pl.DataFrame, b: pl.DataFrame) -> pl.DataFrame:
    """Соединить две монеты по open_time: столбцы A с суффиксом _a, B с суффиксом _b."""
    # Переименовываем все столбцы, кроме времени: close -> close_a / close_b,
    # чтобы после соединения не было одинаковых имён
    a = a.rename({c: f"{c}_a" for c in a.columns if c != "open_time"})
    b = b.rename({c: f"{c}_b" for c in b.columns if c != "open_time"})

    # inner join: остаются только минуты, которые есть у обеих монет
    return a.join(b, on="open_time", how="inner").sort("open_time")


def resample(df: pl.DataFrame, step_ms: int) -> pl.DataFrame:
    """Свечи 1m -> крупнее. open/high/low только по минутам с торговлей."""
    # Условие «в минуте была торговля» — используется в нескольких местах ниже
    traded = pl.col("volume") > 0

    return (
        # Каждой минутке — «корзина»: время начала её крупной свечи
        # (округление вниз: 12:03 -> 12:00, 12:07 -> 12:05)
        df.with_columns((pl.col("open_time") // step_ms * step_ms).alias("bucket"))

        # Минутки с одинаковой корзиной складываем в одну группу
        .group_by("bucket", maintain_order=True)

        # Из каждой группы делаем одну свечу
        .agg(
            # open — первая минута с торговлей (если торговли не было — просто первая)
            pl.col("open").filter(traded).first().fill_null(pl.col("open").first()),
            # high — максимум по минутам с торговлей
            pl.col("high").filter(traded).max().fill_null(pl.col("high").max()),
            # low — минимум по минутам с торговлей
            pl.col("low").filter(traded).min().fill_null(pl.col("low").min()),
            # close — последняя минута (замороженная цена = цена последней сделки, она честная)
            pl.col("close").last(),
            # volume — сумма объёмов всех минут
            pl.col("volume").sum(),
            # сколько минуток попало в свечу (должно быть 5)
            pl.len().alias("n_bars"),
            # сколько из них с торговлей (0 — биржа стояла всю свечу)
            traded.sum().alias("n_traded"),
        )

        # Корзина становится временем свечи
        .rename({"bucket": "open_time"})
        .sort("open_time")
    )


def build_dataset() -> None:
    """Zip-файлы -> проверенные и соединённые пары 1m и 5m в data/processed."""
    # Длина свечи в миллисекундах: 60 000 для 1m, 300 000 для 5m
    step_1m, step_5m = config.STEP_MS["1m"], config.STEP_MS["5m"]

    # 1. Загрузка: все месяцы минуток для ETH (a) и BTC (b)
    a = load_klines(config.SYMBOL_A)
    b = load_klines(config.SYMBOL_B)

    # 2. Проверка качества — отчёт выводится на экран
    print(config.SYMBOL_A, check_bars(a, step_1m))
    print(config.SYMBOL_B, check_bars(b, step_1m))

    # 3. Флаг торговли для минуток: 1 — сделки были, 0 — минута без торговли
    #    (у 5m-свечей такой столбец создаёт resample)
    a = a.with_columns((pl.col("volume") > 0).cast(pl.UInt32).alias("n_traded"))
    b = b.with_columns((pl.col("volume") > 0).cast(pl.UInt32).alias("n_traded"))

    # 4. Пара 1m: ETH и BTC в одной таблице
    pair_1m = align_pair(a, b)

    # 5. Пара 5m: сначала каждую монету собираем в пятиминутки, потом соединяем
    pair_5m = align_pair(resample(a, step_5m), resample(b, step_5m))

    # 6. Сохранение в data/processed (папка создаётся, если её нет)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pair_1m.write_parquet(config.PROCESSED_DIR / "pair_1m.parquet")
    pair_5m.write_parquet(config.PROCESSED_DIR / "pair_5m.parquet")
    print("1m:", pair_1m.shape, "| 5m:", pair_5m.shape)


# Запускается только при `python -m src.prepare`, но не при import из других файлов
if __name__ == "__main__":
    build_dataset()