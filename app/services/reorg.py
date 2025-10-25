from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.nft import NFTTrade
from app.db.models.swap import Swap
from app.utils.logger import logger

from app.db.models.processed_transactions import ProcessedTransaction


async def detect_reorg(current_block_number: int,
                       current_block_hash: str,
                       db: Session = Depends(get_db())) -> Optional[int]:
    """
    Detects if a reorg has occurred by comparing the current block number and hash
    returning the block number if a reorg has occurred.
    Otherwise, returns None.
    """
    try:
        existing_block = (
            db.query(ProcessedTransaction)
            .filter(ProcessedTransaction.block_number == current_block_number)
            .first()
        )

        # Noch kein Eintrag zu diesem Block → kein Reorg
        if not existing_block:
            return None

        # Wenn der BlockHash abweicht → Reorg!
        if existing_block.block_hash != current_block_hash:
            logger.warn(
                "reorg",
                f"Detected reorg at block {current_block_number}",
                {"old_hash": existing_block.block_hash, "new_hash": current_block_hash},
            )
            return current_block_number

        return None

    except Exception as e:
        logger.error("reorg", "Error while checking for reorg", error=e)
        return None
    finally:
        db.close()


async def handle_reorg(from_block: int, db: Session = Depends(get_db())):
    """
    Handles the reorganization (reorg) of the blockchain data by removing entries
    from the database that are associated with blocks greater than or equal
    to the given starting block number. It performs cleanup on swaps, NFT trades,
    and processed transactions to maintain consistency after a reorg event.
    """
    try:
        logger.warn("reorg", f"Starting cleanup from block {from_block}")

        deleted_swaps = db.query(Swap).filter(Swap.block_number >= from_block).delete()
        deleted_nfts = db.query(NFTTrade).filter(NFTTrade.block_number >= from_block).delete()
        deleted_processed = (
            db.query(ProcessedTransaction)
            .filter(ProcessedTransaction.block_number >= from_block)
            .delete()
        )

        db.commit()

        logger.info(
            "reorg",
            "Cleanup completed",
            {
                "from_block": from_block,
                "deleted_swaps": deleted_swaps,
                "deleted_nfts": deleted_nfts,
                "deleted_processed": deleted_processed,
            },
        )

    except Exception as e:
        db.rollback()
        logger.error("reorg", "Error during cleanup", error=e)
    finally:
        db.close()
