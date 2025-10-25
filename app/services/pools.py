from app.api.rpc import get_pool_tokens
from app.db.models.pool import Pool

def get_or_create_pool_info(pool: str, db) -> tuple[str, str]:
    if Pool.exists(db, pool):
        return Pool.get_pool(db, pool).token0, Pool.get_pool(db, pool).token1
    else:
        token0, token1 = get_pool_tokens(pool)
        Pool.add_pool(db, pool, token0, token1)
        return token0, token1