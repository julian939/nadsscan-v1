from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional, Dict, List

from app.db.models.position import Position
from app.utils.logger import logger
from app.utils.utils import normalize_address


def process_swap_for_position(
        wallet: str,
        token_in: str,
        token_out: str,
        amount_in: Decimal,
        amount_out: Decimal,
        mon_address: str,
        db: Session
) -> bool:
    """
    Process a swap and update positions accordingly

    When MON is involved:
    - Buying token: MON out, Token in → Calculate entry price
    - Selling token: Token out, MON in → Calculate exit price

    Args:
        wallet: Wallet address
        token_in: Token received
        token_out: Token sent
        amount_in: Amount received
        amount_out: Amount sent
        mon_address: MON token address
        db: Database session

    Returns:
        True if successful, False otherwise
    """
    wallet = normalize_address(wallet)
    token_in = normalize_address(token_in)
    token_out = normalize_address(token_out)
    mon_address = normalize_address(mon_address)

    try:
        # Case 1: Buying token with MON (token_in is the token, token_out is MON)
        if token_out == mon_address and token_in != mon_address:
            # Price = MON spent / Tokens received
            price_per_token = amount_out / amount_in if amount_in > 0 else Decimal(0)

            Position.update_on_buy(
                db=db,
                wallet=wallet,
                token=token_in,
                buy_amount=amount_in,
                buy_price_mon=price_per_token
            )

            logger.info("positions", f"Position updated - BUY", {
                "wallet": wallet,
                "token": token_in,
                "amount": str(amount_in),
                "price": str(price_per_token),
                "cost": str(amount_out)
            })

            return True

        # Case 2: Selling token for MON (token_out is the token, token_in is MON)
        elif token_in == mon_address and token_out != mon_address:
            # Price = MON received / Tokens sold
            price_per_token = amount_in / amount_out if amount_out > 0 else Decimal(0)

            Position.update_on_sell(
                db=db,
                wallet=wallet,
                token=token_out,
                sell_amount=amount_out,
                sell_price_mon=price_per_token
            )

            logger.info("positions", f"Position updated - SELL", {
                "wallet": wallet,
                "token": token_out,
                "amount": str(amount_out),
                "price": str(price_per_token),
                "revenue": str(amount_in)
            })

            return True

        # Case 3: No MON involved - ignore for position tracking
        else:
            logger.info("positions", "Swap without MON - no position update", {
                "wallet": wallet,
                "token_in": token_in,
                "token_out": token_out
            })
            return True

    except Exception as e:
        logger.error("positions", "Failed to process swap for position", error=e, context={
            "wallet": wallet,
            "token_in": token_in,
            "token_out": token_out
        })
        return False


def get_wallet_portfolio(wallet: str, db: Session) -> Dict:
    """
    Get complete portfolio for a wallet

    Args:
        wallet: Wallet address
        db: Database session

    Returns:
        Dictionary with portfolio statistics
    """
    wallet = normalize_address(wallet)

    try:
        positions = Position.get_active_positions(db, wallet)

        total_value_mon = Decimal(0)
        total_cost_mon = Decimal(0)
        total_realized_pnl = Decimal(0)
        total_unrealized_pnl = Decimal(0)

        position_list = []

        for pos in positions:
            total_cost_mon += pos.total_cost_mon
            total_realized_pnl += pos.realized_pnl_mon or Decimal(0)
            total_unrealized_pnl += pos.unrealized_pnl_mon or Decimal(0)

            current_value = pos.amount * pos.average_entry_price_mon
            total_value_mon += current_value

            position_list.append({
                "token": pos.token,
                "amount": str(pos.amount),
                "avg_entry_price": str(pos.average_entry_price_mon),
                "current_value_mon": str(current_value),
                "total_cost_mon": str(pos.total_cost_mon),
                "realized_pnl_mon": str(pos.realized_pnl_mon or Decimal(0)),
                "unrealized_pnl_mon": str(pos.unrealized_pnl_mon or Decimal(0)),
                "total_pnl_mon": str(Position.get_total_pnl(pos)),
                "total_bought": str(pos.total_bought),
                "total_sold": str(pos.total_sold),
                "trade_count": int(pos.trade_count)
            })

        total_pnl = total_realized_pnl + total_unrealized_pnl

        return {
            "wallet": wallet,
            "position_count": len(positions),
            "total_cost_mon": str(total_cost_mon),
            "total_value_mon": str(total_value_mon),
            "total_realized_pnl_mon": str(total_realized_pnl),
            "total_unrealized_pnl_mon": str(total_unrealized_pnl),
            "total_pnl_mon": str(total_pnl),
            "positions": position_list
        }

    except Exception as e:
        logger.error("positions", "Failed to get wallet portfolio", error=e, context={
            "wallet": wallet
        })
        return {
            "wallet": wallet,
            "error": str(e),
            "positions": []
        }


def get_position_details(wallet: str, token: str, db: Session) -> Optional[Dict]:
    """
    Get detailed information for a specific position

    Args:
        wallet: Wallet address
        token: Token address
        db: Database session

    Returns:
        Dictionary with position details or None
    """
    wallet = normalize_address(wallet)
    token = normalize_address(token)

    try:
        position = Position.get_position(db, wallet, token)

        if not position:
            return None

        return {
            "wallet": wallet,
            "token": token,
            "amount": str(position.amount),
            "average_entry_price_mon": str(position.average_entry_price_mon),
            "total_cost_mon": str(position.total_cost_mon),
            "realized_pnl_mon": str(position.realized_pnl_mon or Decimal(0)),
            "unrealized_pnl_mon": str(position.unrealized_pnl_mon or Decimal(0)),
            "total_pnl_mon": str(Position.get_total_pnl(position)),
            "total_bought": str(position.total_bought),
            "total_sold": str(position.total_sold),
            "trade_count": int(position.trade_count),
            "first_trade_at": position.first_trade_at.isoformat() if position.first_trade_at else None,
            "last_updated": position.last_updated.isoformat() if position.last_updated else None
        }

    except Exception as e:
        logger.error("positions", "Failed to get position details", error=e, context={
            "wallet": wallet,
            "token": token
        })
        return None


def update_unrealized_pnl_for_token(
        token: str,
        current_price_mon: Decimal,
        db: Session
) -> int:
    """
    Update unrealized PnL for all positions holding a specific token

    Used when you have a current price feed

    Args:
        token: Token address
        current_price_mon: Current price per token in MON
        db: Database session

    Returns:
        Number of positions updated
    """
    token = normalize_address(token)

    try:
        # Get all positions for this token
        positions = db.query(Position).filter(
            Position.token == token,
            Position.amount > 0
        ).all()

        count = 0
        for position in positions:
            Position.update_unrealized_pnl(
                db=db,
                wallet=position.wallet,
                token=token,
                current_price_mon=current_price_mon
            )
            count += 1

        logger.info("positions", f"Updated unrealized PnL for {count} positions", {
            "token": token,
            "price": str(current_price_mon)
        })

        return count

    except Exception as e:
        logger.error("positions", "Failed to update unrealized PnL", error=e, context={
            "token": token,
            "price": str(current_price_mon)
        })
        return 0


def get_top_positions_by_pnl(limit: int = 100, db: Session = None) -> List[Dict]:
    """
    Get top positions by total PnL for leaderboard

    Args:
        limit: Number of results to return
        db: Database session

    Returns:
        List of position dictionaries sorted by PnL
    """
    try:
        # Get all positions with non-zero amounts
        positions = db.query(Position).filter(Position.amount > 0).all()

        # Calculate total PnL for each and sort
        positions_with_pnl = []
        for pos in positions:
            total_pnl = Position.get_total_pnl(pos)
            positions_with_pnl.append({
                "wallet": pos.wallet,
                "token": pos.token,
                "amount": str(pos.amount),
                "realized_pnl_mon": str(pos.realized_pnl_mon or Decimal(0)),
                "unrealized_pnl_mon": str(pos.unrealized_pnl_mon or Decimal(0)),
                "total_pnl_mon": str(total_pnl),
                "total_pnl_decimal": total_pnl  # For sorting
            })

        # Sort by total PnL descending
        positions_with_pnl.sort(key=lambda x: x["total_pnl_decimal"], reverse=True)

        # Remove sorting helper and limit results
        result = []
        for pos in positions_with_pnl[:limit]:
            del pos["total_pnl_decimal"]
            result.append(pos)

        return result

    except Exception as e:
        logger.error("positions", "Failed to get top positions", error=e)
        return []


def close_position(wallet: str, token: str, db: Session) -> bool:
    """
    Close (delete) a position completely

    Args:
        wallet: Wallet address
        token: Token address
        db: Database session

    Returns:
        True if closed, False if not found
    """
    wallet = normalize_address(wallet)
    token = normalize_address(token)

    try:
        removed = Position.remove_position(db, wallet, token)

        if removed:
            logger.info("positions", f"Position closed", {
                "wallet": wallet,
                "token": token
            })

        return removed

    except Exception as e:
        logger.error("positions", f"Failed to close position", error=e, context={
            "wallet": wallet,
            "token": token
        })
        raise