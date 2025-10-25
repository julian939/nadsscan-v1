from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional


def normalize_address(address: Optional[str]) -> str:
    """Normalize ethereum address to lowercase and strip whitespace"""
    if not address:
        return ""
    return address.lower().strip()


def normalize_amount(raw: str, decimals: int = 18) -> Decimal:
    """
    Convert raw token amount string to decimal number

    Args:
        raw: Raw amount as string
        decimals: Token decimals (default 18)

    Returns:
        Decimal representation of the amount
    """
    try:
        divisor = Decimal(10) ** decimals
        return Decimal(raw) / divisor
    except Exception:
        return Decimal(0)


def calculate_mon_amount_from_pool_data(
        token0: str,
        token1: str,
        amount0: Decimal,
        amount1: Decimal,
        mon_address: str
) -> Decimal:
    """
    Calculate MON amount from pool token data

    Args:
        token0: First token address
        token1: Second token address
        amount0: Amount of token0
        amount1: Amount of token1
        mon_address: MON token address

    Returns:
        Amount of MON in the transaction
    """
    if token0.lower() == mon_address.lower():
        return abs(amount0)
    elif token1.lower() == mon_address.lower():
        return abs(amount1)
    return Decimal(0)


def get_time_window(period: str) -> datetime:
    """
    Get datetime for start of time period

    Args:
        period: One of "1d", "7d", "30d"

    Returns:
        Datetime object representing start of period

    Raises:
        ValueError: If period is invalid
    """
    now = datetime.utcnow()

    period_map = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    if period not in period_map:
        raise ValueError(f"Invalid period: {period}. Must be one of {list(period_map.keys())}")

    return now - period_map[period]