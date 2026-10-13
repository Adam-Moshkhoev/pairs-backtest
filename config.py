from pathlib import Path

# Пути
ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIGURES_DIR = ROOT / "reports" / "figures"

# Данные
BASE_URL = "https://data.binance.vision/data/futures/um/monthly"
SYMBOL_A, SYMBOL_B = "ETHUSDT", "BTCUSDT"
SYMBOLS = [SYMBOL_A, SYMBOL_B]
RAW_INTERVAL = "1m"      # качаем минутки
INTERVAL = "5m"          # основной таймфрейм, собираем из 1m
FIRST_MONTH, LAST_MONTH = "2024-10", "2026-09"
OOS_START = "2025-10-01" # до этой даты подбор, после — проверка

# Сделка и издержки
NOTIONAL = 10_000.0      # USDT на одну ногу
CAPITAL = 20_000.0
TAKER_FEE_BPS = 5.0
MAKER_FEE_BPS = -0.25    # rebate; единицу уточнить у Георгия
SLIPPAGE_BPS = 1.0