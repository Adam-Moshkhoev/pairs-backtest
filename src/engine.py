import numpy as np
import config
from src.costs import fill_cost


def entry_signal(z: float) -> int:
    """Направление входа: -1 (шорт спреда), +1 (лонг спреда), 0 (нет входа)."""
    if z > config.ENTRY_Z:
        return -1
    elif z < -config.ENTRY_Z:
        return 1
    return 0


def exit_reason(position: int, z: float, bars_held: int) -> str | None:
    """Причина выхода: 'mean', 'stop', 'time' или None (держим)."""
    if (position == -1 and z <= 0) or (position == 1 and z >= 0):
        return "mean"
    if abs(z) > config.STOP_Z:
        return "stop"
    if bars_held >= config.MAX_HOLD_BARS:
        return "time"
    return None


def leg_quantities(direction: int, price_a: float, price_b: float) -> tuple[float, float]:
    """Сколько монет A и B: + купили, − продали. Каждая нога = NOTIONAL $."""
    qty_a = direction * config.NOTIONAL / price_a
    qty_b = -direction * config.NOTIONAL / price_b
    return qty_a, qty_b


def run_backtest(open_a, open_b, close_a, close_b, tradable, z, tier):
    """Главный цикл: на каждой свече A) исполнить план, B) капитал, C) новый план."""
    n = len(z)                              # сколько всего свечей

    # Состояние движка (меняется по ходу)
    cash = config.CAPITAL                   # живые доллары, в начале $20 000
    position = 0                            # 0 нет позиции, -1 шорт спреда, +1 лонг спреда
    qty_a, qty_b = 0.0, 0.0                 # сколько монет ETH и BTC держим (+ купили, − продали)
    bars_held = 0                           # сколько свечей держим текущую позицию
    paused = False                          # пауза после стопа: не входим, пока |z| не < 2
    plan = None                             # записка на следующую свечу: ("enter", ±1) или ("exit", причина)

    # Результаты (заполняем по одной свече)
    equity = np.zeros(n)                    # капитал на каждой свече
    hist_qty_a = np.zeros(n)                # сколько ETH держали на каждой свече
    hist_qty_b = np.zeros(n)                # сколько BTC держали на каждой свече
    trades = []                             # список сделок

    for t in range(n):

        # ── Шаг A: на open исполняем план, если он есть и биржа работала ──
        if plan is not None and tradable[t]:
            action, value = plan            # разбираем записку: что делать и с каким значением

            if action == "enter":
                cash_before = cash                                            # запомнили кошелёк до сделки
                qty_a, qty_b = leg_quantities(value, open_a[t], open_b[t])   # сколько монет на $10 000 в нужную сторону
                cash -= qty_a * open_a[t] + qty_b * open_b[t]                 # купили → деньги ушли, продали → пришли
                cash -= fill_cost(abs(qty_a) * open_a[t], tier)               # комиссия за ETH
                cash -= fill_cost(abs(qty_b) * open_b[t], tier)               # комиссия за BTC
                position = value                                              # запомнили направление позиции
                bars_held = 0                                                 # отсчёт времени с нуля
                trades.append({"entry_t": t, "direction": value, "cash_before": cash_before})

            else:  # action == "exit"
                cash += qty_a * open_a[t] + qty_b * open_b[t]                 # закрыли обе ноги: обратная сделка
                cash -= fill_cost(abs(qty_a) * open_a[t], tier)               # комиссия за ETH
                cash -= fill_cost(abs(qty_b) * open_b[t], tier)               # комиссия за BTC
                trades[-1]["exit_t"] = t                                      # когда вышли
                trades[-1]["reason"] = value                                  # почему: mean / stop / time
                trades[-1]["pnl"] = cash - trades[-1]["cash_before"]          # прибыль сделки с комиссиями
                if value in ("stop", "time"):
                    paused = True                                             # после аварийного выхода — пауза
                position = 0                                                  # позиции больше нет
                qty_a, qty_b = 0.0, 0.0                                       # монет больше нет

            plan = None                     # записка исполнена → выбрасываем

        # ── Шаг B: на close считаем капитал ──
        equity[t] = cash + qty_a * close_a[t] + qty_b * close_b[t]   # кошелёк + стоимость монет
        hist_qty_a[t] = qty_a               # запомнили позицию на этой свече
        hist_qty_b[t] = qty_b

        # ── Шаг C: на close смотрим на z и пишем план на следующую свечу ──
        if plan is None:                    # если старый план ещё ждёт (биржа стояла) — новый не пишем
            if position != 0:               # позиция есть → думаем о выходе
                bars_held += 1                                    # держим ещё одну свечу
                reason = exit_reason(position, z[t], bars_held)   # пора выходить?
                if reason is not None:
                    plan = ("exit", reason)                       # да → выйдем на следующем open
            else:                           # позиции нет → думаем о входе
                if paused and abs(z[t]) < config.ENTRY_Z:
                    paused = False                                # z успокоился → снимаем паузу
                if not paused:
                    direction = entry_signal(z[t])                # есть сигнал на вход?
                    if direction != 0:
                        plan = ("enter", direction)               # да → войдём на следующем open

    return {"equity": equity, "trades": trades, "qty_a": hist_qty_a, "qty_b": hist_qty_b}