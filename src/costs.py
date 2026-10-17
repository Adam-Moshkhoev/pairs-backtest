import config

BPS = 10_000   # 1 bp = 1/10 000


def fill_cost(notional: float, tier: str) -> float:
    """$ издержки одного исполнения: taker-комиссия + проскальзывание."""
    fee_bps = config.FEE_TIER_BPS[tier]["taker"]   # комиссия уровня, bp
    total_bps = fee_bps + config.SLIPPAGE_BPS      # + проскальзывание, bp
    return notional * total_bps / BPS              # bp → доллары