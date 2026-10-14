# Pairs Trading Backtest: ETHUSDT / BTCUSDT

Statistical arbitrage (pairs trading) backtest on Binance USDⓈ-M perpetual futures,
written from scratch in Python (polars, numpy, numba).

## 1. Summary
_TODO: three lines — what was done, main result, conclusion._

## 2. Strategy
- **Spread:** `s = ln(ETH) − β·ln(BTC)` (version 1: β = 1)
- **Signal:** z-score of the spread over a rolling 1-day window
- **Entry:** |z| > 2 — short the expensive leg, long the cheap one, $10,000 per leg
- **Exit:** z returns to 0
- **Stops:** |z| > 4, or position held longer than 2 days

## 3. Data
- **Source:** [data.binance.vision](https://data.binance.vision) — monthly 1m klines and funding rates
- **Instruments:** ETHUSDT, BTCUSDT (USDⓈ-M perpetual futures)
- **Period:** 2024-10-01 – 2026-09-30 (24 months)
- **Timeframes:** 1m downloaded; 5m built from 1m (main timeframe)
- **Quality check (1m):** 1,051,200 bars per symbol, 0 duplicates, 0 gaps, 0 invalid OHLC bars
- **No-trade periods:** 127 (ETH) / 126 (BTC) zero-volume minutes in 7–8 episodes at the same timestamps
  for both symbols (exchange-wide halts; longest 74 min on 2024-10-28). Prices there are carried forward,
  so 5m open/high/low use only traded minutes, and `n_traded` marks incomplete bars.
- **5m validation:** 5m bars built from 1m match Binance's own 5m file for 2024-10 on all 8,928 bars.
- **Output:** `data/processed/pair_1m.parquet` (1,051,200 rows), `pair_5m.parquet` (210,240 rows)
- **Split:** year 1 (2024-10 – 2025-09) for parameter selection, year 2 (2025-10 – 2026-09) out-of-sample

## 4. Backtest assumptions
- Signal on candle close, execution at the next candle's open
- Market orders only → taker fees
- Fee tiers tested: Regular (5 bp), VIP-4 (3 bp), VIP-7 (2.2 bp)
- Slippage: 1 bp per fill
- No trading on bars where either symbol had no trades (`n_traded = 0`)
- Funding: _TODO_
- Capital: $20,000 ($10,000 per leg), no reinvestment

## 5. Results
_TODO_

## 6. Costs and fee sensitivity
_TODO_

## 7. Robustness
_TODO_

## 8. Limitations
_TODO: what candles cannot show — order queue, book depth, partial fills._

## 9. How to run
```bash
conda create -n quant python=3.13 -y
conda activate quant
pip install -r requirements.txt
python -m src.download      # download and verify all data (~97 files)
python -m src.prepare       # check, align and resample → data/processed/*.parquet
```
_TODO: backtest, report._

## 10. Next steps
_TODO_

## 11. Use of LLM
Design choices and debugging were discussed with an LLM; all code was written by me.