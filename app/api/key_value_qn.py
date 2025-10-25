import requests
from typing import List, Optional, Dict, Any

from app.config.config import config
from app.utils.logger import logger

QUICKNODE_KV_BASE_URL = "https://api.quicknode.com/kv/rest/v1"
WALLETS_LIST_KEY = "wallets"


def _make_request(
        method: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Make an authenticated request to QuickNode KV API

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE)
        endpoint: API endpoint path
        payload: Request payload for POST/PATCH

    Returns:
        Response JSON or None on error
    """
    url = f"{QUICKNODE_KV_BASE_URL}/{endpoint}"

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": config.QUICKNODE_API_KEY
    }

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=payload, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=payload, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        logger.error("quicknode_kv", f"HTTP error in {method} {endpoint}", error=e, context={
            "status_code": e.response.status_code if e.response else None,
            "response": e.response.text if e.response else None
        })
        return None

    except requests.exceptions.Timeout as e:
        logger.error("quicknode_kv", f"Timeout in {method} {endpoint}", error=e)
        return None

    except requests.exceptions.RequestException as e:
        logger.error("quicknode_kv", f"Request failed for {method} {endpoint}", error=e)
        return None

    except Exception as e:
        logger.error("quicknode_kv", f"Unexpected error in {method} {endpoint}", error=e)
        return None


def update_wallet_key_value_list(
        add_items: List[str] = [],
        remove_items: List[str] = []
) -> bool:
    """
    Update wallet filter list by adding or removing items

    Args:
        add_items: List of wallet addresses to add
        remove_items: List of wallet addresses to remove

    Returns:
        True if successful, False otherwise
    """
    if not add_items and not remove_items:
        logger.warn("quicknode_kv", "No items to add or remove")
        return True

    payload = {
        "addItems": add_items,
        "removeItems": remove_items
    }

    result = _make_request("PATCH", f"lists/{WALLETS_LIST_KEY}", payload)

    if result:
        logger.info("quicknode_kv", "Updated wallet list", {
            "added": len(add_items),
            "removed": len(remove_items)
        })
        return True

    return False


def create_wallet_key_value_list() -> bool:
    """
    Create the wallets filter list (only needed once)

    Returns:
        True if successful, False otherwise
    """
    payload = {
        "key": WALLETS_LIST_KEY,
        "items": []
    }

    result = _make_request("POST", "lists", payload)

    if result:
        logger.info("quicknode_kv", "Created wallet list")
        return True

    return False


def get_wallet_key_value_list() -> Optional[List[str]]:
    """
    Get current wallet filter list

    Returns:
        List of wallet addresses, or None on error
    """
    result = _make_request("GET", f"lists/{WALLETS_LIST_KEY}")

    if result:
        items = result.get("items", [])
        logger.info("quicknode_kv", "Retrieved wallet list", {"count": len(items)})
        return items

    return None


def delete_wallet_key_value_list() -> bool:
    """
    Delete the entire wallets filter list

    Returns:
        True if successful, False otherwise
    """
    result = _make_request("DELETE", f"lists/{WALLETS_LIST_KEY}")

    if result:
        logger.info("quicknode_kv", "Deleted wallet list")
        return True

    return False


def add_wallet_key_value_list(add_items: List[str]) -> bool:
    """
    Add wallets to a filter list

    Args:
        add_items: List of wallet addresses to add

    Returns:
        True if successful, False otherwise
    """
    return update_wallet_key_value_list(add_items=add_items)


def remove_wallet_key_value_list(remove_items: List[str]) -> bool:
    """
    Remove wallets from a filter list

    Args:
        remove_items: List of wallet addresses to remove

    Returns:
        True if successful, False otherwise
    """
    return update_wallet_key_value_list(remove_items=remove_items)