from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models.wallet import Wallet
from app.api.key_value_qn import add_wallet_key_value_list, remove_wallet_key_value_list
from app.utils.logger import logger
from app.utils.utils import normalize_address


def resolve_wallet(wallet_addresses: List[str], db: Session) -> str:
    """
    Find the first wallet address that exists in the wallets table.

    Args:
        wallet_addresses: List of potential wallet addresses
        db: Database session

    Returns:
        Normalized wallet address if found in database, "unknown" otherwise
    """
    if not wallet_addresses or len(wallet_addresses) == 0:
        logger.warn("wallets", "No wallet addresses provided for resolution")
        return "unknown"

    # Normalize and deduplicate addresses
    normalized_addresses = list(set([normalize_address(addr) for addr in wallet_addresses if addr]))

    # Check each address against database
    for address in normalized_addresses:
        if Wallet.exists(db, address):
            logger.info("wallets", f"Resolved wallet", {"address": address})
            return address

    # If no wallet found in database, return first address or "unknown"
    fallback = normalized_addresses[0] if normalized_addresses else "unknown"
    logger.warn("wallets", f"Wallet not found in database, using fallback", {
        "checked": normalized_addresses,
        "fallback": fallback
    })
    return fallback


def add_wallet(
        wallet_address: str,
        twitter_name: Optional[str] = None,
        twitter_pfp: Optional[str] = None,
        db: Session = None
) -> Optional[Wallet]:
    """
    Add a new wallet to tracking system

    Args:
        wallet_address: Wallet address to track
        twitter_name: Twitter username (optional)
        twitter_pfp: Twitter profile picture URL (optional)
        db: Database session

    Returns:
        Wallet object if successful, None otherwise
    """
    wallet_address = normalize_address(wallet_address)

    if not wallet_address:
        logger.error("wallets", "Invalid wallet address provided")
        return None

    try:
        # Add to database
        wallet = Wallet.add_wallet(db, wallet_address, twitter_name, twitter_pfp)

        if wallet:
            # Add to QuickNode filter list
            try:
                add_wallet_key_value_list([wallet_address])
                logger.info("wallets", f"Wallet added successfully", {
                    "address": wallet_address,
                    "twitter": twitter_name
                })
            except Exception as e:
                logger.error("wallets", f"Failed to add wallet to QuickNode", error=e, context={
                    "address": wallet_address
                })
                # Don't rollback DB transaction if only QuickNode fails

        return wallet

    except Exception as e:
        logger.error("wallets", f"Failed to add wallet", error=e, context={
            "address": wallet_address
        })
        raise


def remove_wallet(wallet_address: str, db: Session) -> bool:
    """
    Remove wallet from tracking system

    Args:
        wallet_address: Wallet address to remove
        db: Database session

    Returns:
        True if removed successfully, False otherwise
    """
    wallet_address = normalize_address(wallet_address)

    if not wallet_address:
        logger.error("wallets", "Invalid wallet address provided")
        return False

    try:
        # Remove from database
        removed = Wallet.remove_wallet(db, wallet_address)

        if removed:
            # Remove from QuickNode filter list
            try:
                remove_wallet_key_value_list([wallet_address])
                logger.info("wallets", f"Wallet removed successfully", {"address": wallet_address})
            except Exception as e:
                logger.error("wallets", f"Failed to remove wallet from QuickNode", error=e, context={
                    "address": wallet_address
                })

        return removed

    except Exception as e:
        logger.error("wallets", f"Failed to remove wallet", error=e, context={
            "address": wallet_address
        })
        raise