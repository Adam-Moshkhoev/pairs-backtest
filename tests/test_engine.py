import numpy as np
from src.engine import entry_signal, exit_reason


# Вход: z > 2 → -1, z < -2 → +1, иначе 0, NaN → 0
def test_entry_signal():
    assert entry_signal(2.5) == -1      # ETH дорогой → шорт спреда
    assert entry_signal(-2.5) == 1     # ETH дешёвый → лонг спреда
    assert entry_signal(1.0) == 0      # норма → ничего
    assert entry_signal(np.nan) == 0   # первые 287 свечей → ничего


# Выход: по норме, по стопу, по времени, держим
def test_exit_reason():
    assert exit_reason(-1, -0.1, 10) == "mean"   # шорт, z прошёл 0
    assert exit_reason(1, 0.2, 10) == "mean"     # лонг, z прошёл 0
    assert exit_reason(-1, 4.5, 10) == "stop"    # шорт, z ушёл за 4
    assert exit_reason(-1, 1.5, 576) == "time"   # держим уже 2 дня
    assert exit_reason(-1, 1.5, 10) is None      # ничего не сработало