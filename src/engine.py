import config


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
