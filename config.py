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
STEP_MS = {"1m": 60_000, "5m": 300_000}   # длина свечи в миллисекундах
FIRST_MONTH, LAST_MONTH = "2024-10", "2026-09"
OOS_START = "2025-10-01" # до этой даты подбор, после — проверка

# Сделка и издержки
NOTIONAL = 10_000.0      # USDT на одну ногу
CAPITAL = 20_000.0
FEE_TIER_BPS = {         # комиссии Binance USDⓈ-M по уровням, б.п.; стратегия использует только taker
    "regular": {"maker": 2.0, "taker": 5.0},
    "vip4":    {"maker": 1.0, "taker": 3.0},
    "vip7":    {"maker": 0.4, "taker": 2.2},
}
SLIPPAGE_BPS = 1.0

# Стратегия
WINDOW = 288          # окно z-score: 288 свечей × 5 мин = 1 день
ENTRY_Z = 2.0         # вход, когда |z| > 2
STOP_Z = 4.0          # стоп, когда |z| > 4
MAX_HOLD_BARS = 576   # тайм-стоп: 576 свечей = 2 дня

# v2 — выбрана на году 1 (ноутбук 05), зафиксирована ДО теста на году 2
V2_WINDOW = 2016      # 7 дней
V2_ENTRY_Z = 2.5