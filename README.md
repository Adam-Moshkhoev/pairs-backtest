# ETH/BTC Pairs Trading — Backtest (Binance USDⓈ-M perpetuals)

A mean-reversion pairs strategy on the ETH/BTC spread, built and backtested from scratch on 5-minute bars (October 2024 – September 2026) with realistic costs: taker fees, slippage and funding.

**How the data was used**

| Period | Dates | Used for |
|--------|-------|----------|
| **Year 1** | Oct 2024 – Sep 2025 (105,120 bars) | all research and every parameter choice |
| **Year 2** | Oct 2025 – Sep 2026 (105,120 bars) | held out, used **once** for the final test |

---

## 1. Summary

| Version | What it is | Year 1 (research), VIP-7 | **Year 2 (test), VIP-7** | **Year 2 (test), Regular** |
|---------|------------|--------------------------|--------------------------|----------------------------|
| **v1** | baseline: 1-day z-score window, entry at \|z\| > 2 | −34.7%, Sharpe −1.76 | −3.2%, Sharpe −0.28 | −31.4%, Sharpe −3.30 |
| **v2** | 7-day z-score window, entry at \|z\| > 2.5 | −8.1%, Sharpe −0.59 | **+8.9%, Sharpe +1.08** | **+4.9%, Sharpe +0.61** |

- **v1 loses money** at every fee tier, in both years.
- **v2 was chosen on year 1 only** (out of ~150 tested variants) and fixed by a git commit before year 2 was opened.
- **v2 beats v1 in both years and at every fee tier**, and is **profitable on the held-out year 2** with a max drawdown of about −7%.
- **But:** v2 trades only ~72 times a year, was still negative on year 1, and is roughly flat over the two years combined. The improvement over v1 is real; a statistically proven edge is not.
- **Main reason:** the ETH/BTC spread mean-reverts only weakly (half-life of 1–6 weeks), so the edge is small.

![Equity v1 and v2](reports/figures/06_equity_v1_v2.png)
![Drawdown v1 and v2](reports/figures/06_drawdown_v1_v2.png)

---

## 2. Strategy

Legs: **A = ETHUSDT**, **B = BTCUSDT** (Binance USDⓈ-M perpetual futures).

1. **Spread:** `s = ln(ETH) − β · ln(BTC)`, β = 1. The spread rises when ETH outperforms BTC.
2. **Z-score:** `z = (s − rolling mean) / rolling std` over the last `window` bars. The window includes the current bar and only looks backwards.
3. **Entry:** `z > entry_z` → **short the spread** (short ETH, long BTC); `z < −entry_z` → **long the spread** (long ETH, short BTC).
4. **Size:** $10,000 notional per leg, fixed. Starting capital $20,000.
5. **Exit (mean):** close when z crosses back to 0.
6. **Stop:** close when |z| > 4.
7. **Time stop:** close after 576 bars (2 days).
8. **Pause:** after a stop or time-stop exit, no new entry until |z| < entry_z.
9. **Execution:** one position at a time; decisions on the bar close, execution at the **next bar's open**; no trade on bars where either leg had no trades; a position still open at the end of the data is closed at the last close (reason `end`).

| Parameter | v1 | v2 |
|-----------|----|----|
| `window` | 288 bars (1 day) | 2016 bars (7 days) |
| `entry_z` | 2.0 | 2.5 |
| exit, stop, time stop, β, size | same | same |

**Example trade.** z = 2.4 with ETH = 2,500 and BTC = 62,500 → short 4 ETH, long 0.16 BTC. Five hours later ETH = 2,475, BTC unchanged, z back to 0 → exit. ETH leg +$100, BTC leg $0, fees (VIP-7) −$12.80 → **+$87.20**.

**v1 has no regime filter.** It enters on |z| > 2 even while the spread is trending. In a steady trend the rolling mean and std follow the spread, so z stays around 2 (for a perfectly linear trend z ≈ √3 ≈ 1.7 regardless of its speed) and the z-stop (|z| > 4) never fires; the trade is closed only by the 2-day time stop. This produced v1's largest losses and is why a regime filter was planned. The filter was tested (4.4) and rejected; the longer z-window of v2 addressed the problem better.

---

## 3. Data, costs and accounting

**Data**
- Binance public data (`data.binance.vision`): USDⓈ-M futures, monthly 1-minute klines and funding-rate files, 2024-10 … 2026-09.
- 1-minute bars → 5-minute bars (open/high/low use only minutes with trades); ETH and BTC aligned on `open_time`. 210,240 bars in total.
- Funding times in the files carry +1 ms; they are rounded to the nearest 5-minute bar.

**Costs** — every fill is a taker fill plus 1 bp slippage; 4 fills per round trip.

| Tier | Taker fee | + slippage | Cost per fill | Cost per round trip ($10k legs) |
|------|-----------|------------|---------------|---------------------------------|
| Regular | 5.0 bp | 1 bp | 6.0 bp | $24.00 |
| VIP-4 | 3.0 bp | 1 bp | 4.0 bp | $16.00 |
| VIP-7 | 2.2 bp | 1 bp | 3.2 bp | $12.80 |

**Funding** — every 8 hours, at the start of the funding bar and before that bar's planned trade, at the bar's open price: `payment = qty × price × rate` (longs pay when the rate is positive). Funding never affects decisions (verified by a test). Because the two legs are opposite, payments largely cancel: effect on v1 over two years was +$182 (< 1%).

**Accounting** — `cash −= qty_a·price_a + qty_b·price_b + fees` (signs handle long/short); `equity = cash + qty_a·close_a + qty_b·close_b`.

**Metrics** — total return; max drawdown; Sharpe = mean / std (ddof = 1) of daily returns × √365 (risk-free = 0); win rate; average trade; profit factor (gross wins / gross losses); exposure (share of bars in a position). Sharpe is reported as NaN if equity ever falls to zero or below.

---

## 4. How the backtest was checked

| Check | How | Result |
|-------|-----|--------|
| Money is counted correctly | 6-bar example with every dollar calculated by hand (equity on each bar, fees, PnL 176.12) | exact match |
| Stops and new rules | hand-calculated cases: loss stop (PnL −264.144), β-sized BTC leg (0.24 BTC, PnL 50.192), early exit (PnL 56.048) | exact match |
| Fast engine = reference engine | numba engine vs Python engine on hand cases and 5,000 random bars with funding | identical trades, equity and positions; numba 46× faster |
| No look-ahead | z-score test: a centred window (which looks into the future) must fail the test | passes only with the backward window |
| Funding does not change decisions | same trades with and without funding | identical |
| New code does not change old results | after every change the year-1 baseline was re-run | always −34.7%, Sharpe −1.76 |
| Bankrupt runs | a test where equity dips below zero between daily samples | Sharpe = NaN, `min_equity` shows it |
| Notebooks agree | year 1 in the final notebook (06) vs research notebook (05); quarterly sums vs yearly totals | identical |

**42 tests** in `tests/` (`pytest -v`).

**A bug found and fixed during research:** one grid cell (12-hour window, entry 1.5) showed Sharpe **+0.99** while its return was **−107%** — equity had gone below zero, and daily returns (change ÷ yesterday's equity) became meaningless. Since then Sharpe is NaN for any run whose equity touches zero, and every table shows `min_equity`.

---

## 5. Research on year 1 — step by step

Rules used throughout:
- **one change at a time**, compared with the year-1 baseline;
- every run logged in `reports/research_log_year1.csv` (~150 variants) — notebook `05_research_year1.ipynb`;
- a change is accepted only if it improves **a region of neighbouring settings (a plateau)**, at both VIP-7 and Regular — not a single lucky point;
- year 2 is not touched.

All numbers in this section: **year 1, VIP-7** unless stated.

### Step 0 — v1 baseline: where the money is lost

| | Trades | Win rate | Avg trade | Profit factor | Return | Max DD | Sharpe |
|-|--------|----------|-----------|---------------|--------|--------|--------|
| VIP-7 | 483 | 61.7% | −$14.35 | 0.768 | −34.7% | −37.2% | −1.76 |
| Regular | 483 | 58.2% | −$25.56 | 0.614 | −61.7% | −63.1% | −3.17 |

Exits by reason (VIP-7):

| Exit | Trades | Avg PnL | Total PnL | Avg holding |
|------|--------|---------|-----------|-------------|
| mean | 384 | +$32 | +$12,467 | 11 h |
| stop | 92 | −$155 | −$14,269 | 4 h |
| time | 6 | **−$851** | −$5,108 | 48 h |
| end | 1 | −$21 | −$21 | — |

The 10 worst trades:

| Month | Exit | PnL | z_long at entry | Deviation at entry |
|-------|------|-----|-----------------|--------------------|
| May 2025 | time | −$1,906 | 0.97 | 200 bp |
| Jul 2025 | time | −$1,219 | 0.92 | 119 bp |
| Aug 2025 | time | −$851 | 0.74 | 93 bp |
| Feb 2025 | stop | −$505 | −2.89 | 478 bp |
| Aug 2025 | time | −$491 | −0.92 | 177 bp |
| Jan 2025 | stop | −$468 | −0.96 | 115 bp |
| Aug 2025 | mean | −$465 | 1.35 | 196 bp |
| Dec 2024 | stop | −$464 | 0.24 | 116 bp |
| Nov 2024 | mean | −$450 | 1.31 | 119 bp |
| Sep 2025 | time | −$433 | −0.23 | 123 bp |

**Key finding:** the 10 worst trades (2% of trades) lost **−$7,253**, more than the whole year (**−$6,931**). The typical trade is profitable.

![Worst trades](reports/figures/07_worst_trades.png)

### 4.1 Stop by dollar loss per trade — rejected

**Idea:** the z-stop misses trends, so also stop on money: exit when the open trade is down more than a threshold (exit at the next open, reason `loss`, then pause). Two ways to set the threshold:
- **% of the $10k leg** (a fixed dollar amount: 2% = $200 ≈ the spread moved 2% against us);
- **% of equity at entry** (stricter as equity falls).

| Variant | Trades | Win rate | Avg trade | PF | Return | Max DD | Sharpe |
|---------|--------|----------|-----------|----|--------|--------|--------|
| **baseline** | 483 | 61.7% | −14.35 | 0.768 | **−34.7%** | −37.2% | **−1.76** |
| 1% of leg ($100) | 641 | 51.3% | −10.65 | 0.811 | −34.1% | −35.8% | −2.01 |
| 1.5% of leg | 579 | 57.2% | −13.05 | 0.787 | −37.8% | −39.2% | −2.19 |
| 2% of leg | 546 | 59.9% | −14.55 | 0.771 | −39.7% | −42.4% | −2.18 |
| 3% of leg | 516 | 60.9% | −17.87 | 0.731 | −46.1% | −48.5% | −2.42 |
| 5% of leg ($500) | 496 | 61.5% | −15.38 | 0.758 | −38.1% | −40.7% | −1.96 |
| 0.5% of equity | 714 | 43.1% | −13.64 | 0.746 | −48.7% | −49.8% | −3.03 |
| 0.75% of equity | 616 | 53.4% | −12.34 | 0.792 | −38.0% | −39.7% | −2.10 |
| 1% of equity | 574 | 58.2% | −13.42 | 0.782 | −38.5% | −40.8% | −2.23 |
| 1.5% of equity | 536 | 60.8% | −15.31 | 0.763 | −41.0% | −43.5% | −2.17 |
| 2.5% of equity | 498 | 61.4% | −14.72 | 0.765 | −36.7% | −39.3% | −1.92 |

Regular: every variant checked was worse than baseline (−69% … −78% vs −61.7%).

**Why it fails:** many trades temporarily lose $100–500 and then revert to the mean with a profit; the stop turns those into real losses (win rate drops to 43–61%) and adds trades and fees (1% of leg: +158 trades ≈ −$2,000 in fees). **Sharpe is worse in all 10 variants → rejected** (code kept, off by default).

![Loss stop](reports/figures/07_loss_stop.png)

### 4.4 Regime filter at entry — rejected (diagnosis only, engine unchanged)

**Question:** can a bad trade be recognised **at the moment of entry**?

*Feature 1 — weekly z (`z_long`, 7-day window).* Hypothesis: large |z_long| = the spread has trended all week = bad trade. The data said the opposite:

| \|z_long\| at entry | Trades | Avg PnL | Total |
|---------------------|--------|---------|-------|
| ≤ 1 | 236 | −25.6 | −6,051 |
| 1 – 1.5 | 111 | −17.9 | −1,989 |
| 1.5 – 2 | 64 | +13.3 | +848 |
| 2 – 2.5 | 33 | −18.5 | −610 |
| 2.5 – 3 | 17 | +3.6 | +62 |
| > 3 | 13 | +79.0 | +1,027 |

*Feature 2 — deviation of the spread from its mean, in bp* (≈ the dollar profit if it fully reverts). Five equal groups (~95 trades each):

| Deviation | Avg PnL | Median PnL | Win rate | Total |
|-----------|---------|------------|----------|-------|
| 48 bp | −14.3 | +24.3 | 68% | −1,358 |
| 75 bp | +0.9 | +29.7 | 64% | +86 |
| 103 bp | −52.7 | +20.6 | 53% | −4,957 |
| 147 bp | −14.7 | +41.4 | 59% | −1,399 |
| 278 bp | +9.6 | +68.2 | 63% | +915 |

- No consistent link between either feature and PnL; even the smallest deviation (48 bp) is 4× the VIP-7 cost, so costs are not the issue.
- **The median trade is profitable in every group** (+$20 … +$68). Group averages are driven by a few huge losers.
- The 10 worst trades had ordinary z_long and deviation at entry (see the table in Step 0): **the trend starts after entry**, so no entry filter on these features can separate them. **Rejected.**

### 4.2 Shorter time stop — rejected

| Time stop | Trades | Win rate | PF | Return | Max DD | Sharpe |
|-----------|--------|----------|----|--------|--------|--------|
| 8 h | 593 | 49.9% | 0.721 | −45.1% | −46.9% | −2.79 |
| 12 h | 544 | 53.9% | 0.712 | −48.4% | −50.2% | −2.75 |
| 16 h | 520 | 58.1% | 0.731 | −44.0% | −45.8% | −2.48 |
| 24 h | 501 | 61.1% | 0.783 | −32.6% | −35.7% | −1.75 |
| 36 h | 487 | 61.2% | 0.760 | −36.2% | −38.8% | −1.85 |
| **48 h (baseline)** | 483 | 61.7% | 0.768 | −34.7% | −37.2% | −1.76 |

Many good trades need 16–24 h to revert; cutting earlier destroys them. 24 h is ≈ baseline with worse neighbours → noise. **Rejected.**

![Time stop](reports/figures/07_time_stop.png)

### 4.3 Grid: z-window × entry threshold — **accepted → v2**

Instead of changing exits around the signal, change the signal itself: 7 windows (12 h … 14 days) × 4 entry thresholds.

Sharpe, VIP-7:

| window | 1.5 | 2.0 | 2.5 | 3.0 |
|--------|-----|-----|-----|-----|
| 144 (12 h) | bankrupt | −2.90 | −3.48 | −3.86 |
| 288 (1 d, v1) | −2.33 | **−1.76** | −1.53 | −2.35 |
| 576 (2 d) | −2.34 | −2.37 | −2.31 | −2.43 |
| 1152 (4 d) | −0.94 | −1.12 | −0.78 | −1.27 |
| 2016 (7 d) | −0.79 | −0.89 | **−0.59** | −1.26 |
| 2880 (10 d) | −0.67 | −0.47 | −1.03 | −1.59 |
| 4032 (14 d) | −2.11 | −1.33 | −0.50 | +0.65 |

Return, VIP-7:

| window | 1.5 | 2.0 | 2.5 | 3.0 |
|--------|-----|-----|-----|-----|
| 144 | −106.8% | −96.1% | −67.0% | −56.3% |
| 288 (v1) | −48.7% | −34.7% | −28.0% | −35.5% |
| 576 | −45.3% | −41.1% | −37.3% | −31.3% |
| 1152 | −17.3% | −19.2% | −12.4% | −16.7% |
| 2016 | −12.2% | −12.3% | **−9.1%** | −15.5% |
| 2880 | −10.5% | −7.7% | −12.9% | −17.9% |
| 4032 | −24.1% | −15.7% | −6.8% | +4.9% |

Trades per year:

| window | 1.5 | 2.0 | 2.5 | 3.0 |
|--------|-----|-----|-----|-----|
| 144 | 1088 | 854 | 663 | 453 |
| 288 | 593 | 483 | 368 | 274 |
| 576 | 315 | 244 | 187 | 143 |
| 1152 | 193 | 142 | 111 | 91 |
| 2016 | 123 | 90 | 74 | 53 |
| 2880 | 109 | 75 | 53 | 36 |
| 4032 | 81 | 58 | 39 | 27 |

Sharpe, Regular:

| window | 1.5 | 2.0 | 2.5 | 3.0 |
|--------|-----|-----|-----|-----|
| 144 | bankrupt | bankrupt | bankrupt | −5.34 |
| 288 (v1) | −3.79 | −3.17 | −2.70 | −3.40 |
| 576 | −3.25 | −3.18 | −2.96 | −3.04 |
| 1152 | −1.58 | −1.61 | −1.21 | −1.66 |
| 2016 | −1.22 | −1.23 | −0.91 | −1.55 |
| 2880 | −1.05 | −0.77 | −1.29 | −1.79 |
| 4032 | −2.41 | −1.57 | −0.68 | +0.49 |

- **Plateau:** windows of 4–10 days × entry 1.5–2.5 — all 12 cells have Sharpe −0.47 … −1.12 (v1: −1.76), at both fee tiers. Losses are 2–4× smaller.
- The positive cell (14 days, 3.0) is an isolated peak on **27 trades** with worse neighbours → not chosen.
- **v2 = centre of the plateau: window 2016 (7 days), entry 2.5.**

![Grid](reports/figures/05_grid_sharpe.png)

**Why the long window works** (year 1, VIP-7):

| | v1 (288, 2.0) | v2 (2016, 2.5) |
|-|---------------|----------------|
| Trades | 483 | 74 |
| mean exits: n / avg PnL / avg holding | 384 / +$32 / 11 h | 18 / **+$371** / 26 h |
| stop exits: n / avg PnL | 92 / −$155 | 19 / −$245 |
| time exits: n / avg PnL | 6 / **−$851** | 37 / −$98 |
| Total | −$6,931 | −$1,627 |

The 7-day window only reacts to large dislocations: a successful reversion earns ~10× more, $12.80 of fees becomes small next to it, and the catastrophic time-stop losses disappear. But half of v2's trades (37 of 74) hit the 2-day time stop → tested next.

![Exits by reason](reports/figures/07_exit_reasons.png)

### 4.2b Longer time stop for long windows — rejected

Windows 1152 / 2016 / 2880 × time stop 2 / 4 / 7 / 14 days × entry 2.0 / 2.5. Sharpe, VIP-7:

Entry 2.0:

| window | 2 d | 4 d | 7 d | 14 d |
|--------|-----|-----|-----|------|
| 1152 | −1.12 | −1.04 | −0.95 | −0.95 |
| 2016 | −0.89 | −0.48 | −0.97 | −0.60 |
| 2880 | −0.47 | −0.47 | −0.97 | −0.92 |

Entry 2.5:

| window | 2 d | 4 d | 7 d | 14 d |
|--------|-----|-----|-----|------|
| 1152 | −0.78 | −1.02 | −0.80 | −0.80 |
| 2016 | −0.59 | −0.70 | −0.37 | −0.21 |
| 2880 | −1.03 | −1.46 | −1.23 | −0.98 |

Only one row (2016, 2.5) improves with a longer time stop; its neighbours do not. The difference (−8.1% → −5.0%) is ≈ $620 ≈ 2 trades → noise. **Time stop stays at 2 days.**

![Time stop for long windows](reports/figures/07_hold_grid.png)

### 4.5 Rolling hedge ratio β — rejected

**Diagnosis:** β of ETH on BTC (5-minute returns) over year 1 = **1.18**, and it **rose every quarter**: 1.01 → 1.12 → 1.42 → 1.47. v1's worst trades were in Q2–Q3, where β ≈ 1.4–1.5: with β = 1, a market move looks like a divergence.

**Implementation:**
- rolling β = cov(rETH, rBTC) / var(rBTC) over the last N bars;
- spread built from returns, `cumsum(rETH − β_prev · rBTC)` — with a changing β, `ln(ETH) − β·ln(BTC)` would jump by ~11% when β moves by 0.01, because ln(BTC) ≈ 11;
- BTC leg = β × $10,000, β fixed at the entry decision.

Sharpe, VIP-7:

| Version | β = 1 | rolling β, 7 d | 14 d | 30 d |
|---------|-------|----------------|------|------|
| v1 | **−1.76** | −3.58 | −3.27 | −3.82 |
| v2 | **−0.59** | −1.01 | −1.15 | −0.90 |

Rolling β values were sane (0.68 … 1.94, mean 1.27) and v2's trade structure barely changed (72 vs 74 trades; more mean exits, but costlier time exits), so this is not a bug. Likely reason: with β = 1 part of the market move stays in the spread, also mean-reverts on short horizons, and the strategy earned on it. **Rejected** (code kept, off by default).

![Beta experiment](reports/figures/07_beta.png)

### Robustness of v2 by quarter (year 1)

| Quarter | v1 | v2 | v2 better? |
|---------|----|----|------------|
| 2024-Q4 | −3,189 | +476 | ✅ |
| 2025-Q1 | +1,691 | −160 | ❌ |
| 2025-Q2 | −1,131 | +159 | ✅ |
| 2025-Q3 | −4,302 | −2,102 | ✅ |
| **Year** | **−6,931** | **−1,627** | |

v2 beats v1 in 3 of 4 quarters and is near zero in three; almost all of its loss is Q3 (a trending quarter, β ≈ 1.47).

![Quarters](reports/figures/07_quarters.png)

### 4.6 Exit before zero — rejected

Exit when z has come back to `exit_z` instead of 0 (short: z ≤ exit_z; long: z ≥ −exit_z), to rescue the trades that time out.

| exit_z | Trades | Win rate | PF | Return VIP-7 | Sharpe VIP-7 | Sharpe Regular |
|--------|--------|----------|----|--------------|--------------|----------------|
| **0 (v2)** | 74 | 44.6% | 0.846 | **−8.1%** | **−0.59** | **−0.91** |
| 0.25 | 76 | 46.1% | 0.875 | −6.6% | −0.49 | −0.84 |
| 0.5 | 76 | 47.4% | 0.816 | −9.7% | −0.76 | −1.11 |
| 0.75 | 76 | 50.0% | 0.788 | −11.0% | −0.90 | −1.26 |
| 1.0 | 77 | 50.6% | 0.696 | −15.3% | −1.39 | −1.78 |

Win rate rises, but exiting early gives up more of the good trades (~$371 each) than it saves. 0.25 is ≈ 1 trade better (noise); the rest is a steady decline. **Rejected.**

![Exit before zero](reports/figures/07_exit_z.png)

### Half-life of the spread (measurement only)

Regression `Δs_t = a + b · s_(t−1)`; half-life = −ln 2 / ln(1 + b).

| Period | b | Half-life |
|--------|---|-----------|
| Year 1 | −0.000023 | 103 days |
| 2024-Q4 | −0.000375 | 6.4 days |
| 2025-Q1 | −0.000058 | 41.6 days |
| 2025-Q2 | −0.000089 | 27.0 days |
| 2025-Q3 | −0.000109 | 22.1 days |

The spread is close to a random walk and its speed of reversion changes a lot. This explains why a 1-day window mostly trades noise, why longer windows work better, and why even the best version is near zero. (This half-life is measured against one mean for the whole period, while the strategy uses a rolling mean, so it is a rough indicator.)

![Beta and half-life](reports/figures/07_beta_halflife.png)

### Not tuned on purpose

- **stop_z:** v2 has ~19 stops a year; tuning it would fit a handful of trades.
- Every rejected rule (loss stop, rolling β, exit_z) stays in the code, **off by default**, so the notebook can reproduce every table above.

### Decision

**v2 = window 2016 (7 days), entry 2.5**; everything else as in v1. Written to `config.py` (`V2_WINDOW`, `V2_ENTRY_Z`) and committed (*"Фиксация v2 до теста на году 2"*) **before** year 2 was opened.

---

## 6. Final test on year 2 (run once)

Notebook `06_final_test.ipynb`. Each year is a separate run starting from $20,000.

| Version | Tier | Trades | Win rate | Return | Max DD | Sharpe | Min equity |
|---------|------|--------|----------|--------|--------|--------|------------|
| v1 | Regular | 504 | 53.2% | −31.4% | −36.9% | −3.30 | $13,609 |
| v1 | VIP-4 | 504 | 59.3% | −11.3% | −20.9% | −1.12 | $17,565 |
| v1 | VIP-7 | 504 | 61.3% | −3.2% | −14.9% | −0.28 | $19,112 |
| **v2** | Regular | 72 | 56.9% | **+4.9%** | −7.6% | **+0.61** | $19,766 |
| **v2** | VIP-4 | 72 | 59.7% | **+7.7%** | −7.0% | **+0.95** | $19,794 |
| **v2** | VIP-7 | 72 | 59.7% | **+8.9%** | −6.7% | **+1.08** | $19,805 |

Year 1 vs year 2:

| Version | Tier | Year 1 return / Sharpe | Year 2 return / Sharpe |
|---------|------|------------------------|------------------------|
| v1 | Regular | −61.7% / −3.17 | −31.4% / −3.30 |
| v1 | VIP-4 | −42.4% / −2.17 | −11.3% / −1.12 |
| v1 | VIP-7 | −34.7% / −1.76 | −3.2% / −0.28 |
| v2 | Regular | −12.3% / −0.91 | +4.9% / +0.61 |
| v2 | VIP-4 | −9.3% / −0.68 | +7.7% / +0.95 |
| v2 | VIP-7 | −8.1% / −0.59 | +8.9% / +1.08 |

In dollars (start $20,000):

| v2 | Year 1 | Year 2 | Both years (sum) |
|----|--------|--------|------------------|
| Regular | −$2,459 | +$970 | −$1,489 |
| VIP-4 | −$1,865 | +$1,546 | −$319 |
| VIP-7 | −$1,627 | +$1,776 | +$149 |

**Conclusions**
1. v2 beats v1 in both years and at every fee tier → the long window is a real improvement, not a fit to year 1.
2. On year 2 v2 is profitable even on Regular fees: with only 72 trades, costs barely matter.
3. Risk is low: max drawdown ≈ −7%, equity never below ≈ $19,770.
4. Year 2 was easier for both versions (v1 also improved), so part of the profit is the market regime. The gap between v1 and v2 held.

---

## 7. Costs and edge per turnover

Turnover = 4 fills × $10,000 per round trip. Gross edge = PnL before fees ÷ turnover (approximate, from the results above).

| Version | Period | Trades | Turnover | Gross edge | Covers costs? |
|---------|--------|--------|----------|------------|---------------|
| v1 | 2 years | 987 | $39.5M | ≈ +1.2 bp | no (costs 3.2–6 bp) |
| v2 | 2 years | 146 | $5.8M | ≈ +3.5 bp | ≈ break-even at VIP-7 (3.2 bp) |
| v2 | year 2 | 72 | $2.9M | ≈ +9.4 bp | yes, all tiers |

v1 needs > 6 bp per fill to break even on Regular and makes 1.2 bp. v2 earns more per dollar traded because it trades rarely and only on large deviations.

---

## 8. Limitations

- **Small sample:** ~72 trades a year for v2. A Sharpe of ~1 over one year is not statistically significant; a handful of trades can flip a year.
- **Year 2 was favourable** for both versions; over two years combined v2 is roughly flat. On year 1, v2 lost money even with tuned parameters.
- **One pair**, and it mean-reverts weakly (half-life 1–6 weeks, unstable).
- **v1's year-2 result had been seen before** the final test (on 18.10); for v2 the final test was the first look at year 2.
- **Fixed $10k legs:** leverage grows as equity falls (v1 reached ~16× at its worst). v2's equity stayed above ≈ $18,000 across both years.
- **β = 1**; a rolling hedge ratio was tested and did not help.
- Taker fills with flat 1 bp slippage; no market-impact model; no maker orders.
- One position at a time; no regime filter (tested, rejected).

## 9. Next steps

1. **Walk-forward:** re-select the window every quarter on the previous 12 months and trade the next quarter — the market changes (β 1.0 → 1.5, half-life 6–42 days), so parameters need regular re-tuning.
2. **Other pairs** with stronger mean reversion (cointegration test, half-life in days).
3. **Trend-following on the same spread:** v1's biggest losses came from trends; build on year 1 only, test once on year 2.
4. **Equity-based position sizing** instead of fixed $10k legs.
5. **Maker / limit execution** to cut costs.

---

## 10. Output for the team

`reports/positions_v1.parquet` and `reports/positions_v2.parquet` — one row per symbol per 5-minute bar, both years (positions do not depend on the fee tier):

| column | type | meaning |
|--------|------|---------|
| `symbol` | str | ETHUSDT or BTCUSDT |
| `timestamp` | datetime | bar open time (UTC) |
| `position_qty` | float | coins held (negative = short) |
| `close_price` | float | bar close price |

Example (v2): `ETHUSDT −4.07` and `BTCUSDT +0.161` on 2024-10-09 15:20 = short ETH $10k, long BTC $10k. v2 is in a position 26% of the time (v1: 54%).

## 11. How to run

```bash
# 1. install dependencies (Python 3.13)
pip install -r requirements.txt

# 2. download raw data and build 5-minute bars (data/ is not in git)
python -m src.download
python -m src.prepare

# 3. run tests (42 tests)
pytest -v

# 4. notebooks, in order
#    01_data_check → 02_first_backtest → 03_funding → 04_numba_speed
#    → 05_research_year1 → 06_final_test → 07_report_figures
```

## 12. Project structure

```
config.py                     paths, symbols, fees, strategy parameters (v1 and v2)
requirements.txt              Python dependencies
pytest.ini                    test settings
.gitignore                    data/ and caches are not committed
DEVLOG.md                     day-by-day log
README.md

data/                         raw Binance files and processed 5m bars (created by download/prepare)

src/
  __init__.py
  download.py                 download Binance monthly files (klines, funding)
  prepare.py                  1m → 5m bars, pair alignment
  signals.py                  log spread, rolling z-score, rolling β, hedged spread
  costs.py                    cost per fill (fee + slippage)
  funding.py                  funding rates mapped to bars
  engine.py                   reference Python engine (v1)
  engine_numba.py             fast engine (numba): same results as engine.py + optional rules
  metrics.py                  return, drawdown, Sharpe, trade stats
  research.py                 one evaluation run on year 1
  export.py                   positions in the team format

tests/                        42 tests
  test_prepare.py             5m bars: time step, no duplicates, valid OHLC, resampling
  test_signals.py             spread, z-score, no look-ahead, rolling β, hedged spread
  test_costs.py               cost per fill and per round trip
  test_engine.py              hand-calculated trades, end-of-data close, funding
  test_engine_numba.py        numba = Python engine; loss stop, β leg size, exit_z
  test_metrics.py             return, drawdown, Sharpe, trade stats, bankrupt → Sharpe NaN
  test_funding.py             rounding to bars, mapping rates to bars
  test_export.py              team output format

notebooks/
  01_data_check.ipynb         data quality: gaps, duplicates, OHLC checks
  02_first_backtest.ipynb     v1 backtest: metrics, PnL by exit reason, worst trades, positions_v1
  03_funding.ipynb            funding rates: loading, effect on PnL (+$182 over 2 years)
  04_numba_speed.ipynb        numba engine: same results as Python, 46× faster
  05_research_year1.ipynb     all experiments on year 1 (4.1–4.6, grid, β, half-life) → choice of v2
  06_final_test.ipynb         one-time test of v1 and v2 on year 2, equity charts, positions_v2
  07_report_figures.ipynb     charts for this README (from the research log; no new tuning)

reports/
  figures/                    all charts used in this README
  positions_v1.parquet        v1 positions, team format
  positions_v2.parquet        v2 positions, team format
  research_log_year1.csv      every variant tried on year 1
```
