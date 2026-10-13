"""Скачивание свечей и фандинга с data.binance.vision."""
import hashlib
import urllib.request
from pathlib import Path

import config


def month_range(first: str, last: str) -> list[str]:
    """'2024-10', '2026-09' -> ['2024-10', '2024-11', ..., '2026-09']."""

    year = int(first[:4])
    month = int(first[5:7])
    end_year = int(last[:4])
    end_month = int(last[5:7])

    months = []
    while year < end_year or (year == end_year and month <= end_month):
        months.append(f"{year}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def kline_url(symbol: str, interval: str, month: str) -> str:
    """Адрес zip-файла свечей за месяц."""
    return f"{config.BASE_URL}/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"


def funding_url(symbol: str, month: str) -> str:
    """Адрес zip-файла фандинга за месяц."""
    return f"{config.BASE_URL}/fundingRate/{symbol}/{symbol}-fundingRate-{month}.zip"

def download_file(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)
    return dest


def verify_checksum(zip_path: Path, checksum_path: Path) -> bool:
    """Сравнить SHA-256 zip-файла с хешем из файла .CHECKSUM."""
    expected_hash = checksum_path.read_text().split()[0]
    actual_hash = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    return expected_hash == actual_hash

def fetch_verified(url: str, dest: Path) -> bool:
    """Скачать файл и его .CHECKSUM, проверить хеш. Если хеш не совпал — удалить файл."""
    checksum_dest = dest.with_name(dest.name + ".CHECKSUM")
    download_file(url, dest)                     # сам zip
    download_file(url + ".CHECKSUM", checksum_dest)       # его отпечаток
    if verify_checksum(dest, checksum_dest):
        return True
    dest.unlink()                               # повреждённый файл удаляем
    return False

def download_all() -> None:
    """Скачать все свечи и весь фандинг для всех символов и месяцев."""
    months = month_range(config.FIRST_MONTH, config.LAST_MONTH)              # из config
    failed = []                                 # сюда — файлы, которые не прошли проверку

    for symbol in [config.SYMBOL_A, config.SYMBOL_B]:                          # обе монеты из config
        for month in months:
            # 1. Свечи
            url = kline_url(symbol, config.RAW_INTERVAL, month) # какой таймфрейм качаем? (см. config)
            dest = config.RAW_DIR / "klines" / symbol / url.split("/")[-1]
            ok = fetch_verified(url, dest)
            print("OK  " if ok else "FAIL", dest.name)
            if not ok:
                failed.append(dest.name)

            # 2. Фандинг — то же самое
            url = funding_url(symbol, month)
            dest = config.RAW_DIR / "funding" / symbol / url.split("/")[-1]
            ok = fetch_verified(url, dest)
            print("OK  " if ok else "FAIL", dest.name)
            if not ok:
                failed.append(dest.name)

    # 3. Один месяц 5m — для проверки сборки 5m из 1m в prepare.py
    url = kline_url(config.SYMBOL_A, "5m", config.FIRST_MONTH)
    fetch_verified(url, config.RAW_DIR / "klines_5m_check" / url.split("/")[-1])

    print(f"Готово. Не прошли проверку: {len(failed)}")
    for name in failed:
        print("  ", name)


if __name__ == "__main__":
    download_all()