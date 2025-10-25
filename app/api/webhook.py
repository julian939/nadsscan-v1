from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional, List
import asyncio

from app.config.config import config
from app.services.swaps import process_swap_event
#from app.services.swaps import process_swap_event
#from app.services.nfts import process_nft_event
from app.utils.logger import logger

router = APIRouter()


@router.post("/webhook")
async def quicknode_webhook(
    request: Request,
    auth: Optional[str] = Header(None)
):
    """
    QuickNode Webhook Endpoint.
    - Receives Swap- and NFT-Events from quicknode stream
    - authenthicates the stream header
    - sends data to service workers asynchron
    """

    # --- Authenthication ---
    if auth != config.QUICKNODE_SECURITY_TOKEN:
        logger.warn("webhook", "Unauthorized webhook request rejected")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # --- Reading Payload ---
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("webhook", "Invalid JSON payload received", error=e)
        raise HTTPException(status_code=400, detail="Invalid JSON")

    swaps: List[dict] = payload.get("swaps", [])
    nft_trades: List[dict] = payload.get("nftTrades", [])

    logger.info(
        "webhook",
        f"Incoming QuickNode payload",
        {"swaps": len(swaps), "nft_trades": len(nft_trades)}
    )

    # --- Event-Handling ---
    tasks = []
    for swap in swaps:
        tasks.append(asyncio.create_task(process_swap_event(swap)))
    #for nft_trade in nft_trades:
    #    tasks.append(asyncio.create_task(process_nft_event(nft_trade)))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # --- Error-Handling ---
    error_count = 0
    for result in results:
        if isinstance(result, Exception):
            error_count += 1
            logger.error("webhook", "Error during event processing", error=result)

    logger.info(
        "webhook",
        f"Processed events summary",
        {"swaps": len(swaps), "nft_trades": len(nft_trades), "errors": error_count}
    )

    return {"status": "ok", "processed_swaps": len(swaps), "processed_nfts": len(nft_trades), "errors": error_count}
