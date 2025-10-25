from sqlalchemy.orm import Session
from typing import Optional

from app.db.models.processed_transactions import ProcessedTransaction
from app.db.models.swap import Swap
from app.db.models.nft import NFTTrade
from app.utils.logger import logger


def detect_reorg(
        current_block_number: int,
        current_block_hash: str,
        db: Session
) -> Optional[int]:
    """
    Detects if a blockchain reorganization has occurred

    Args:
        current_block_number: Block number from incoming event
        current_block_hash: Block hash from incoming event
        db: Database session

    Returns:
        Block number where reorg occurred, or None if no reorg detected
    """
    try:
        # Check if we have processed transactions for this block
        existing_tx = ProcessedTransaction.get_by_block(db, current_block_number)

        # No existing entry for this block → no reorg
        if not existing_tx:
            return None

        # Block hash mismatch → reorg detected!
        if existing_tx.block_hash != current_block_hash:
            logger.warn("reorg", f"Blockchain reorg detected at block {current_block_number}", {
                "old_hash": existing_tx.block_hash,
                "new_hash": current_block_hash
            })
            return current_block_number

        return None

    except Exception as e:
        logger.error("reorg", "Error while checking for reorg", error=e, context={
            "block_number": current_block_number,
            "block_hash": current_block_hash
        })
        # Return None instead of raising - don't stop processing on reorg check failure
        return None


def handle_reorg(from_block: int, db: Session) -> dict:
    """
    Handle blockchain reorganization by removing affected data

    Args:
        from_block: Block number to start cleanup from (inclusive)
        db: Database session

    Returns:
        Dictionary with cleanup statistics
    """
    try:
        logger.warn("reorg", f"Starting reorg cleanup from block {from_block}")

        # Delete all swaps from affected blocks
        deleted_swaps = (
            db.query(Swap)
            .filter(Swap.block_number >= from_block)
            .delete(synchronize_session=False)
        )

        # Delete all NFT trades from affected blocks
        deleted_nfts = (
            db.query(NFTTrade)
            .filter(NFTTrade.block_number >= from_block)
            .delete(synchronize_session=False)
        )

        # Delete processed transaction markers
        deleted_processed = (
            db.query(ProcessedTransaction)
            .filter(ProcessedTransaction.block_number >= from_block)
            .delete(synchronize_session=False)
        )

        # Commit all deletions
        db.commit()

        result = {
            "from_block": from_block,
            "deleted_swaps": deleted_swaps,
            "deleted_nfts": deleted_nfts,
            "deleted_processed": deleted_processed
        }

        logger.info("reorg", "Reorg cleanup completed successfully", result)

        return result

    except Exception as e:
        db.rollback()
        logger.error("reorg", "Error during reorg cleanup", error=e, context={
            "from_block": from_block
        })
        raise