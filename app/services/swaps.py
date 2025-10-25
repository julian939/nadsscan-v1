from decimal import Decimal

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config.config import config
from app.db.database import get_db
from app.db.models.processed_transactions import ProcessedTransaction
from app.db.models.swap import Swap
from app.services.pools import get_or_create_pool_info
from app.services.reorg import detect_reorg, handle_reorg
from app.services.wallets import resolve_wallet
from app.utils.logger import logger
from app.utils.utils import normalize_amount

MON_ADDRESS = config.MON_ADDRESS

def is_sell_swap(event: dict) -> bool:
    return event.get("tokenOut", "").lower() == MON_ADDRESS


def _map_tokens_and_amounts(event: dict, db: Session = Depends(get_db())):
    """
    Gibt token_in, token_out, amount_in_raw, amount_out_raw, amount_in, amount_out zurück.
    Logik:
     - token0/token1 from pool
     - amount0/amount1 aus event
     - token_in = Token, dessen amount < 0 (vom wallet gesendet)
     - token_out = Token, dessen amount > 0 (zum wallet empfangen)
    """
    pool = event.get("pool", "").lower()
    amount0_raw = event.get("amount0", "0")
    amount1_raw = event.get("amount1", "0")

    try:
        token0, token1 = get_or_create_pool_info(pool, db)
    except Exception as e:
        logger.error("swaps", f"Failed to resolve pool tokens for {pool}", error=e)
        return None

    # parse as Decimal for sign detection
    try:
        a0 = Decimal(amount0_raw)
    except Exception:
        a0 = Decimal(0)
    try:
        a1 = Decimal(amount1_raw)
    except Exception:
        a1 = Decimal(0)

    # determine which token was sent (negative amount) and which received (positive)
    token_in = None
    token_out = None
    amount_in_raw = None
    amount_out_raw = None
    amount_in = Decimal(0)
    amount_out = Decimal(0)

    # Case: token0 is sent (a0 < 0)
    if a0 < 0 and a1 > 0:
        token_in = token0
        token_out = token1
        amount_in_raw = str(abs(a0))
        amount_out_raw = str(abs(a1))
        amount_in = normalize_amount(str(abs(a0)))
        amount_out = normalize_amount(str(abs(a1)))
    # Case: token1 is sent (a1 < 0)
    elif a1 < 0 < a0:
        token_in = token1
        token_out = token0
        amount_in_raw = str(abs(a1))
        amount_out_raw = str(abs(a0))
        amount_in = normalize_amount(str(abs(a1)))
        amount_out = normalize_amount(str(abs(a0)))
    else:
        # Fallback: falls beide positiv/negativ oder ungewöhnlich – versuche heuristik
        # Wenn one amount is zero, use the other as in/out by sign
        if a0 != 0:
            if a0 < 0:
                token_in = token0
                token_out = token1
                amount_in_raw = str(abs(a0))
                amount_in = normalize_amount(amount_in_raw)
                amount_out_raw = str(abs(a1))
                amount_out = normalize_amount(amount_out_raw)
            else:
                token_in = token1
                token_out = token0
                amount_in_raw = str(abs(a1))
                amount_in = normalize_amount(amount_in_raw)
                amount_out_raw = str(abs(a0))
                amount_out = normalize_amount(amount_out_raw)
        else:
            # give up, store raws as-is and set tokens
            token_in = token0
            token_out = token1
            amount_in_raw = amount0_raw
            amount_out_raw = amount1_raw
            amount_in = normalize_amount(amount_in_raw)
            amount_out = normalize_amount(amount_out_raw)

    return {
        "token_in": token_in,
        "token_out": token_out,
        "amount_in_raw": amount_in_raw,
        "amount_out_raw": amount_out_raw,
        "amount_in": amount_in,
        "amount_out": amount_out,
    }


async def process_swap_event(event: dict, db: Session = Depends(get_db())):
    tx_hash = event.get("txHash")
    try:
        block_number = int(event.get("blockNumber"))
        block_hash = event.get("blockHash")
    except Exception:
        block_number = None
        block_hash = None

    try:
        # Reorg-check
        if block_number is not None and block_hash is not None:
            reorg_block = await detect_reorg(block_number, block_hash, db)
            if reorg_block:
                await handle_reorg(reorg_block, db)
                logger.warn("swaps", f"Reorg detected → cleanup done at block {reorg_block}")

        # Duplicate check
        if ProcessedTransaction.is_processed(db, tx_hash):
            logger.info("swaps", f"Skipping already processed tx {tx_hash}")
            return

        # Map tokens & amounts (uses pool_manager -> RPC if unknown)
        mapped = _map_tokens_and_amounts(event)
        if not mapped:
            logger.info("swaps", f"Ignored swap because pool mapping failed or unknown: {tx_hash}",
                     {"pool": event.get("pool")})
            return

        token_in = mapped["token_in"]
        token_out = mapped["token_out"]
        amount_in_raw = mapped["amount_in_raw"]
        amount_out_raw = mapped["amount_out_raw"]
        amount_in = mapped["amount_in"]
        amount_out = mapped["amount_out"]

        # mon_amount: if either token_in or token_out is MON, compute MON value
        mon_amount = Decimal(0)
        is_sell = False
        if token_in == MON_ADDRESS:
            mon_amount = amount_in
            # selling MON -> token_out
            is_sell = True
        elif token_out == MON_ADDRESS:
            mon_amount = amount_out
            # buying MON (receiving MON) -> is_sell False
            is_sell = False
        else:
            # No MON involved
            logger.info("swaps", "Ignored swap without MON involvement (no MON in pool tokens)", {"tx_hash": tx_hash})
            return

        # Resolve wallet: prefer wallets table matching sender/recipient
        sender = (event.get("sender") or "").lower()
        recipient = (event.get("recipient") or "").lower()
        arg_from = (event.get("from") or "").lower()
        arg_to = (event.get("to") or "").lower()
        wallets = [sender, recipient, arg_from, arg_to]
        wallet_addr = resolve_wallet(wallets, db)

        Swap.add_swap(db, tx_hash, block_number, block_hash, event.get("pool", "").lower(),
                      token_in, token_out, amount_in_raw, amount_out_raw, amount_in, amount_out,
                      mon_amount, is_sell, wallet_addr)

        ProcessedTransaction.add_processed(db, tx_hash, block_number, block_hash)

        logger.info("swaps", f"Processed swap {tx_hash}", {"wallet": wallet_addr, "mon_amount": str(mon_amount)})

    except Exception as e:
        db.rollback()
        logger.error("swaps", f"Error processing swap {tx_hash}", error=e)
    finally:
        db.close()
