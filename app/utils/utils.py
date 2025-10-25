from datetime import datetime, timedelta
from decimal import Decimal
from app.config.config import config
from app.services.pools import get_or_create_pool_info

MON_ADDRESS: str = config.MON_ADDRESS

def calculate_mon_amount(event: dict, db) -> Decimal:
    pool_address = event.get("pool", "").lower()
    if not pool_address:
        return Decimal(0)

    token0, token1 = get_or_create_pool_info(pool_address, db)
    amount0 = Decimal(event.get("amount0", "0"))
    amount1 = Decimal(event.get("amount1", "0"))

    if token0 == MON_ADDRESS:
        return amount0 / Decimal(1e18)
    elif token1 == MON_ADDRESS:
        return amount1 / Decimal(1e18)
    return Decimal(0)


def normalize_amount(raw: str) -> Decimal:
    """ Convert raw string to decimal number """
    try:
        return Decimal(raw) / Decimal(10 ** 18)
    except Exception:
        return Decimal(0)


def get_time_window(period: str):
    now = datetime.utcnow()
    if period == "1d":
        return now - timedelta(days=1)
    elif period == "7d":
        return now - timedelta(days=7)
    elif period == "30d":
        return now - timedelta(days=30)
    raise ValueError("Invalid period")