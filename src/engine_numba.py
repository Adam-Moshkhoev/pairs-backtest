import numpy as np
from numba import njit
import config

REASONS = {1: "mean", 2: "stop", 3: "time", 4: "end"}     # код причины → текст (для обёртки)


@njit
def _core(open_a, open_b, close_a, close_b, tradable, z, funding_a, funding_b,
          fee_frac, notional, capital, entry_z, stop_z, max_hold):
    n = len(z)

    # Состояние
    cash = capital
    position = 0
    qty_a = 0.0
    qty_b = 0.0
    bars_held = 0
    paused = False
    plan_action = 0          # 0 — нет плана, 1 — вход, 2 — выход
    plan_value = 0           # вход: направление ±1; выход: код причины 1..3

    # Результаты по свечам
    equity = np.zeros(n)
    hist_a = np.zeros(n)
    hist_b = np.zeros(n)

    # Сделки: массивы «с запасом» + счётчик k
    tr_entry = np.zeros(n, dtype=np.int64)
    tr_exit = np.zeros(n, dtype=np.int64)
    tr_dir = np.zeros(n, dtype=np.int64)
    tr_reason = np.zeros(n, dtype=np.int64)
    tr_pnl = np.zeros(n)
    tr_funding = np.zeros(n)
    tr_cash_before = np.zeros(n)
    k = 0                    # сколько сделок открыто к этому моменту

    for t in range(n):

        # ── Фандинг (до исполнения плана) ──
        if position != 0 and (funding_a[t] != 0 or funding_b[t] != 0):
            pay = qty_a * open_a[t] * funding_a[t] + qty_b * open_b[t] * funding_b[t]
            cash -= pay
            tr_funding[k - 1] -= pay                          # текущая сделка — последняя открытая

        # ── Шаг A: исполнить план ──
        if plan_action != 0 and tradable[t]:
            if plan_action == 1:                             # вход
                tr_cash_before[k] = cash
                qty_a = plan_value * notional / open_a[t]    # как leg_quantities
                qty_b = -plan_value * notional / open_b[t]
                cash -= qty_a * open_a[t] + qty_b * open_b[t]
                cash -= abs(qty_a) * open_a[t] * fee_frac    # как fill_cost
                cash -= abs(qty_b) * open_b[t] * fee_frac    # как fill_cost
                position = plan_value
                bars_held = 0
                tr_entry[k] = t
                tr_dir[k] = plan_value
                k += 1                                       # новая сделка
            else:                                            # выход (plan_action == 2)
                cash += qty_a * open_a[t] + qty_b * open_b[t]
                cash -= abs(qty_a) * open_a[t] * fee_frac
                cash -= abs(qty_b) * open_b[t] * fee_frac
                tr_exit[k - 1] = t
                tr_reason[k - 1] = plan_value
                tr_pnl[k - 1] = cash - tr_cash_before[k - 1]
                if plan_value == 2 or plan_value == 3:       # stop или time
                    paused = True
                position = 0
                qty_a = 0.0
                qty_b = 0.0
            plan_action = 0

        # ── Шаг B: капитал ──
        equity[t] = cash + qty_a * close_a[t] + qty_b * close_b[t]
        hist_a[t] = qty_a
        hist_b[t] = qty_b

        # ── Шаг C: новый план ──
        if plan_action == 0:
            if position != 0:
                bars_held += 1
                # как exit_reason: mean → stop → time
                if (position == -1 and z[t] <= 0) or (position == 1 and z[t] >= 0):
                    plan_action, plan_value = 2, 1
                elif abs(z[t]) > stop_z:
                    plan_action, plan_value = 2, 2
                elif bars_held >= max_hold:
                    plan_action, plan_value = 2, 3              
            else:
                if paused and abs(z[t]) < entry_z:
                    paused = False
                if not paused:
                    # как entry_signal
                    if z[t] > entry_z:
                        plan_action, plan_value = 1, -1
                    elif z[t] < -entry_z:
                        plan_action, plan_value = 1, 1

    # ── Закрыть открытую позицию в конце данных ──
    if position != 0:
        t = n - 1
        cash += qty_a * close_a[t] + qty_b * close_b[t]
        cash -= abs(qty_a) * close_a[t] * fee_frac
        cash -= abs(qty_b) * close_b[t] * fee_frac
        tr_exit[k - 1] = t
        tr_reason[k - 1] = 4                               # end
        tr_pnl[k - 1] = cash - tr_cash_before[k - 1]
        equity[t] = cash

    return (equity, hist_a, hist_b,
            tr_entry[:k], tr_exit[:k], tr_dir[:k], tr_reason[:k], tr_pnl[:k], tr_funding[:k])


def run_backtest_fast(open_a, open_b, close_a, close_b, tradable, z, tier,
                      funding_a=None, funding_b=None,
                      entry_z=config.ENTRY_Z, stop_z=config.STOP_Z, max_hold=config.MAX_HOLD_BARS):
    """То же, что run_backtest, но цикл скомпилирован numba. Результат в том же формате."""
    n = len(z)
    if funding_a is None:
        funding_a = np.zeros(n)
    if funding_b is None:
        funding_b = np.zeros(n)
    fee_frac = (config.FEE_TIER_BPS[tier]["taker"] + config.SLIPPAGE_BPS) / 10000   # bp → доля

    eq, ha, hb, e, x, d, r, p, f = _core(
        open_a, open_b, close_a, close_b, tradable, z, funding_a, funding_b,
        fee_frac, config.NOTIONAL, config.CAPITAL, entry_z, stop_z, max_hold)

    trades = [
        {"entry_t": int(e[i]), "exit_t": int(x[i]), "direction": int(d[i]),
         "reason": REASONS[int(r[i])], "pnl": float(p[i]), "funding": float(f[i])}
        for i in range(len(e))
    ]
    return {"equity": eq, "trades": trades, "qty_a": ha, "qty_b": hb}