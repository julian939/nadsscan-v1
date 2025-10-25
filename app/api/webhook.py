from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional, List
import asyncio

from app.config.config import config
from app.db.database import SessionLocal
from app.services.swaps import process_swap_event
from app.utils.logger import logger

router = APIRouter()


async def process_swap_with_session(swap: dict) -> dict:
    """
    Process a single swap event with its own database session

    Args:
        swap: Swap event data

    Returns:
        Result dictionary with success status and event info
    """
    db = SessionLocal()
    try:
        success = process_swap_event(swap, db)
        return {
            "success": success,
            "tx_hash": swap.get("txHash", "unknown"),
            "error": None
        }
    except Exception as e:
        logger.error("webhook", f"Failed to process swap", error=e, context={
            "tx_hash": swap.get("txHash", "unknown")
        })
        return {
            "success": False,
            "tx_hash": swap.get("txHash", "unknown"),
            "error": str(e)
        }
    finally:
        db.close()


@router.post("/webhook")
async def quicknode_webhook(
        request: Request,
        auth: Optional[str] = Header(None)
):
    """
    QuickNode Webhook Endpoint

    - Receives Swap and NFT events from QuickNode stream
    - Authenticates using security token
    - Processes events concurrently with individual database sessions

    Returns:
        JSON with processing statistics
    """

    # --- Authentication ---
    if auth != config.QUICKNODE_SECURITY_TOKEN:
        logger.warn("webhook", "Unauthorized webhook request rejected", {
            "auth_header_present": auth is not None
        })
        raise HTTPException(status_code=401, detail="Unauthorized")

    # --- Parse Payload ---
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("webhook", "Invalid JSON payload received", error=e)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    swaps: List[dict] = payload.get("swaps", [])
    nft_trades: List[dict] = payload.get("nftTrades", [])

    logger.info("webhook", f"Received QuickNode webhook payload", {
        "swaps": len(swaps),
        "nft_trades": len(nft_trades)
    })

    # --- Process Swaps ---
    if not swaps and not nft_trades:
        logger.warn("webhook", "Empty payload received")
        return {
            "status": "ok",
            "processed_swaps": 0,
            "processed_nfts": 0,
            "errors": 0
        }

    # Create tasks for concurrent processing
    # Each task gets its own database session
    tasks = []
    for swap in swaps:
        tasks.append(asyncio.create_task(process_swap_with_session(swap)))

    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # --- Analyze Results ---
    success_count = 0
    error_count = 0
    error_details = []

    for result in results:
        if isinstance(result, Exception):
            error_count += 1
            error_details.append({
                "error": str(result),
                "type": type(result).__name__
            })
            logger.error("webhook", "Task failed with exception", error=result)
        elif isinstance(result, dict):
            if result.get("success"):
                success_count += 1
            else:
                error_count += 1
                if result.get("error"):
                    error_details.append({
                        "tx_hash": result.get("tx_hash"),
                        "error": result.get("error")
                    })
        else:
            error_count += 1
            error_details.append({"error": "Unknown result type"})

    logger.info("webhook", f"Webhook processing completed", {
        "total_swaps": len(swaps),
        "successful": success_count,
        "failed": error_count
    })

    response = {
        "status": "ok",
        "processed_swaps": len(swaps),
        "successful": success_count,
        "errors": error_count
    }

    # Include error details if there were failures
    if error_details and len(error_details) <= 10:  # Only include if not too many
        response["error_details"] = error_details

    return response