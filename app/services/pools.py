from sqlalchemy.orm import Session
from typing import Tuple

from app.api.rpc import get_pool_tokens
from app.db.models.pool import Pool
from app.utils.logger import logger


def get_or_create_pool_info(pool_address: str, db: Session) -> Tuple[str, str]:
    """
    Get pool token information from database or fetch from RPC

    Args:
        pool_address: Pool contract address
        db: Database session

    Returns:
        Tuple of (token0, token1) addresses

    Raises:
        Exception: If unable to fetch pool tokens
    """
    pool_address = pool_address.lower()

    # Try to get from database first
    if Pool.exists(db, pool_address):
        pool = Pool.get_pool(db, pool_address)
        if pool:
            logger.info("pools", f"Pool found in database", {"pool": pool_address})
            return pool.token0, pool.token1

    # Fetch from RPC if not in database
    try:
        logger.info("pools", f"Fetching pool tokens from RPC", {"pool": pool_address})
        token0, token1 = get_pool_tokens(pool_address)

        # Store in database for future use
        Pool.add_pool(db, pool_address, token0, token1)

        logger.info("pools", f"Pool added to database", {
            "pool": pool_address,
            "token0": token0,
            "token1": token1
        })

        return token0, token1

    except Exception as e:
        logger.error("pools", f"Failed to get pool info for {pool_address}", error=e)
        raise