from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal

from app.db.database import get_db
from app.services.positions import (
    get_wallet_portfolio,
    get_position_details,
    get_top_positions_by_pnl,
    update_unrealized_pnl_for_token
)
from app.utils.logger import logger
from app.utils.utils import normalize_address

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("/wallet/{wallet_address}")
async def get_wallet_positions(
        wallet_address: str,
        db: Session = Depends(get_db)
):
    """
    Get complete portfolio for a wallet

    Returns:
        - All active positions
        - Total PnL (realized + unrealized)
        - Position statistics
    """
    try:
        wallet_address = normalize_address(wallet_address)

        if not wallet_address:
            raise HTTPException(status_code=400, detail="Invalid wallet address")

        portfolio = get_wallet_portfolio(wallet_address, db)

        if "error" in portfolio:
            raise HTTPException(status_code=500, detail=portfolio["error"])

        return portfolio

    except HTTPException:
        raise
    except Exception as e:
        logger.error("positions_api", "Failed to get wallet positions", error=e, context={
            "wallet": wallet_address
        })
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/wallet/{wallet_address}/token/{token_address}")
async def get_position(
        wallet_address: str,
        token_address: str,
        db: Session = Depends(get_db)
):
    """
    Get details for a specific position

    Returns:
        - Position size
        - Entry price
        - Realized and unrealized PnL
        - Trade statistics
    """
    try:
        wallet_address = normalize_address(wallet_address)
        token_address = normalize_address(token_address)

        if not wallet_address or not token_address:
            raise HTTPException(status_code=400, detail="Invalid addresses")

        position = get_position_details(wallet_address, token_address, db)

        if not position:
            raise HTTPException(status_code=404, detail="Position not found")

        return position

    except HTTPException:
        raise
    except Exception as e:
        logger.error("positions_api", "Failed to get position", error=e, context={
            "wallet": wallet_address,
            "token": token_address
        })
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/leaderboard")
async def get_leaderboard(
        limit: int = Query(default=100, ge=1, le=500),
        db: Session = Depends(get_db)
):
    """
    Get top positions by total PnL

    Query Parameters:
        - limit: Number of results (1-500, default 100)

    Returns:
        List of top positions sorted by PnL descending
    """
    try:
        top_positions = get_top_positions_by_pnl(limit=limit, db=db)

        return {
            "count": len(top_positions),
            "limit": limit,
            "positions": top_positions
        }

    except Exception as e:
        logger.error("positions_api", "Failed to get leaderboard", error=e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/update-unrealized-pnl")
async def update_unrealized_pnl(
        token_address: str,
        current_price_mon: str,
        db: Session = Depends(get_db)
):
    """
    Update unrealized PnL for all positions of a token

    Use this when you have a current price feed

    Body:
        - token_address: Token contract address
        - current_price_mon: Current price per token in MON

    Returns:
        Number of positions updated
    """
    try:
        token_address = normalize_address(token_address)

        if not token_address:
            raise HTTPException(status_code=400, detail="Invalid token address")

        try:
            price = Decimal(current_price_mon)
            if price <= 0:
                raise ValueError("Price must be positive")
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid price: {str(e)}")

        count = update_unrealized_pnl_for_token(token_address, price, db)

        return {
            "token": token_address,
            "price_mon": str(price),
            "positions_updated": count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("positions_api", "Failed to update unrealized PnL", error=e, context={
            "token": token_address,
            "price": current_price_mon
        })
        raise HTTPException(status_code=500, detail="Internal server error")