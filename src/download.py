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

def download_all() -> None:
    """Скачать все свечи и весь фандинг для всех символов и месяцев."""
    ...


if __name__ == "__main__":
    download_all()