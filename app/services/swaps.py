from decimal import Decimal
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.config.config import config
from app.db.models.processed_transactions import ProcessedTransaction
from app.db.models.swap import Swap
from app.services.pools import get_or_create_pool_info
from app.services.reorg import detect_reorg, handle_reorg
from app.services.wallets import resolve_wallet
from app.utils.logger import logger
from app.utils.utils import normalize_amount, normalize_address

MON_ADDRESS = config.MON_ADDRESS


def _map_tokens_and_amounts(event: dict, db: Session) -> Optional[Dict[str, Any]]:
    """
    Map pool tokens and amounts from swap event

    Determines which token was sent (token_in) and received (token_out)
    based on the sign of amount0 and amount1.

    Args:
        event: Swap event data
        db: Database session

    Returns:
        Dictionary with token_in, token_out, amounts, or None if mapping fails
    """
    pool = normalize_address(event.get("pool", ""))
    amount0_raw = event.get("amount0", "0")
    amount1_raw = event.get("amount1", "0")

    if not pool:
        logger.warn("swaps", "Missing pool address in event")
        return None

    # Get pool tokens from database or RPC
    try:
        token0, token1 = get_or_create_pool_info(pool, db)
    except Exception as e:
        logger.error("swaps", f"Failed to resolve pool tokens for {pool}", error=e)
        return None

    # Parse amounts as Decimal for sign detection
    try:
        a0 = Decimal(amount0_raw)
        a1 = Decimal(amount1_raw)
    except Exception as e:
        logger.error("swaps", "Failed to parse amounts", error=e, context={
            "amount0": amount0_raw,
            "amount1": amount1_raw
        })
        return None

    # Determine token flow based on amount signs
    # Negative amount = token sent (in)
    # Positive amount = token received (out)

    token_in = None
    token_out = None
    amount_in_raw = "0"
    amount_out_raw = "0"

    if a0 < 0 < a1:
        # token0 sent, token1 received
        token_in = token0
        token_out = token1
        amount_in_raw = str(abs(a0))
        amount_out_raw = str(abs(a1))
    elif a1 < 0 < a0:
        # token1 sent, token0 received
        token_in = token1
        token_out = token0
        amount_in_raw = str(abs(a1))
        amount_out_raw = str(abs(a0))
    else:
        # Fallback for unusual cases
        logger.warn("swaps", "Unusual amount pattern in swap", {
            "pool": pool,
            "amount0": amount0_raw,
            "amount1": amount1_raw
        })
        # Use absolute values and try to determine direction
        if abs(a0) > 0:
            token_in = token0 if a0 < 0 else token1
            token_out = token1 if a0 < 0 else token0
            amount_in_raw = str(abs(a0))
            amount_out_raw = str(abs(a1))
        else:
            token_in = token1 if a1 < 0 else token0
            token_out = token0 if a1 < 0 else token1
            amount_in_raw = str(abs(a1))
            amount_out_raw = str(abs(a0))

    # Normalize amounts from raw values
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


def process_swap_event(event: dict, db: Session) -> bool:
    """
    Process a single swap event from QuickNode webhook

    Args:
        event: Swap event data from QuickNode
        db: Database session

    Returns:
        True if processed successfully, False otherwise
    """
    tx_hash = event.get("txHash")

    if not tx_hash:
        logger.error("swaps", "Missing transaction hash in event")
        return False

    try:
        # Parse block information
        try:
            block_number = int(event.get("blockNumber", 0))
            block_hash = event.get("blockHash", "")
        except (ValueError, TypeError) as e:
            logger.error("swaps", f"Invalid block data in tx {tx_hash}", error=e)
            return False

        if not block_number or not block_hash:
            logger.error("swaps", f"Missing block data in tx {tx_hash}")
            return False

        # Check for blockchain reorganization
        reorg_block = detect_reorg(block_number, block_hash, db)
        if reorg_block is not None:
            handle_reorg(reorg_block, db)
            logger.warn("swaps", f"Handled reorg at block {reorg_block}")

        # Check if already processed
        if ProcessedTransaction.is_processed(db, tx_hash):
            logger.info("swaps", f"Skipping duplicate tx {tx_hash}")
            return True

        # Map tokens and amounts
        mapped = _map_tokens_and_amounts(event, db)
        if not mapped:
            logger.warn("swaps", f"Failed to map tokens for tx {tx_hash}", {
                "pool": event.get("pool")
            })
            return False

        token_in = mapped["token_in"]
        token_out = mapped["token_out"]
        amount_in = mapped["amount_in"]
        amount_out = mapped["amount_out"]
        amount_in_raw = mapped["amount_in_raw"]
        amount_out_raw = mapped["amount_out_raw"]

        # Calculate MON amount and determine if it's a sell
        mon_amount = Decimal(0)
        is_sell = False

        if token_in == MON_ADDRESS:
            mon_amount = amount_in
            is_sell = True  # Selling MON for other token
        elif token_out == MON_ADDRESS:
            mon_amount = amount_out
            is_sell = False  # Buying MON with other token
        else:
            # No MON involved in this swap
            logger.info("swaps", f"Ignoring non-MON swap tx {tx_hash}", {
                "token_in": token_in,
                "token_out": token_out
            })
            # Mark as processed to avoid reprocessing
            ProcessedTransaction.add_processed(db, tx_hash, block_number, block_hash)
            return True

        # Resolve wallet address
        sender = normalize_address(event.get("sender", ""))
        recipient = normalize_address(event.get("recipient", ""))
        from_addr = normalize_address(event.get("from", ""))
        to_addr = normalize_address(event.get("to", ""))

        potential_wallets = [addr for addr in [sender, recipient, from_addr, to_addr] if addr]
        wallet_addr = resolve_wallet(potential_wallets, db)

        # Store swap in database
        Swap.add_swap(
            db=db,
            tx_hash=tx_hash,
            block_number=block_number,
            block_hash=block_hash,
            pool=normalize_address(event.get("pool", "")),
            token_in=token_in,
            token_out=token_out,
            amount_in_raw=amount_in_raw,
            amount_out_raw=amount_out_raw,
            amount_in=amount_in,
            amount_out=amount_out,
            mon_amount=mon_amount,
            is_sell=is_sell,
            wallet=wallet_addr
        )

        # Mark as processed
        ProcessedTransaction.add_processed(db, tx_hash, block_number, block_hash)

        # Update position tracking
        from app.services.positions import process_swap_for_position
        position_updated = process_swap_for_position(
            wallet=wallet_addr,
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            amount_out=amount_out,
            mon_address=MON_ADDRESS,
            db=db
        )

        if not position_updated:
            logger.warn("swaps", f"Position update failed for swap {tx_hash}")

        logger.info("swaps", f"Successfully processed swap {tx_hash}", {
            "wallet": wallet_addr,
            "mon_amount": str(mon_amount),
            "is_sell": is_sell,
            "block": block_number,
            "position_updated": position_updated
        })

        return True

    except Exception as e:
        db.rollback()
        logger.error("swaps", f"Error processing swap {tx_hash}", error=e)
        return False