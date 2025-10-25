import requests
from typing import Any, List, Tuple
from time import sleep

from app.config.config import config
from app.utils.logger import logger

FUNC_TOKEN0 = "0x0dfe1681"
FUNC_TOKEN1 = "0xd21220a7"

MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def call_rpc(method: str, params: List[Any], retry_count: int = 0) -> Any:
    """
    Sends a json rpc to the official monad rpc endpoint with retry logic.

    Args:
        method: RPC method name
        params: List of parameters
        retry_count: Current retry attempt (internal use)

    Returns:
        Result from RPC call

    Raises:
        ValueError: If RPC returns an error
        Exception: For connection/timeout errors after retries
    """
    try:
        response = requests.post(
            config.MONAD_RPC_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            error_msg = result["error"].get("message", "Unknown RPC error")
            raise ValueError(f"RPC error: {error_msg}")

        return result.get("result")

    except requests.exceptions.Timeout as e:
        if retry_count < MAX_RETRIES:
            logger.warn("rpc", f"RPC timeout, retrying ({retry_count + 1}/{MAX_RETRIES})", {
                "method": method
            })
            sleep(RETRY_DELAY * (retry_count + 1))
            return call_rpc(method, params, retry_count + 1)
        else:
            logger.error("rpc", f"RPC timeout after {MAX_RETRIES} retries", error=e, context={
                "method": method,
                "params": params
            })
            raise

    except requests.exceptions.RequestException as e:
        if retry_count < MAX_RETRIES:
            logger.warn("rpc", f"RPC connection error, retrying ({retry_count + 1}/{MAX_RETRIES})", {
                "method": method,
                "error": str(e)
            })
            sleep(RETRY_DELAY * (retry_count + 1))
            return call_rpc(method, params, retry_count + 1)
        else:
            logger.error("rpc", f"RPC failed after {MAX_RETRIES} retries", error=e, context={
                "method": method,
                "params": params
            })
            raise

    except Exception as e:
        logger.error("rpc", "Unexpected RPC error", error=e, context={
            "method": method,
            "params": params
        })
        raise


def get_pool_tokens(pool_address: str) -> Tuple[str, str]:
    """
    Get token0 and token1 addresses from a pool contract via RPC.

    Args:
        pool_address: Pool contract address

    Returns:
        Tuple of (token0, token1) addresses

    Raises:
        ValueError: If RPC returns invalid data
        Exception: For RPC connection errors
    """
    pool_address = pool_address.lower()

    try:
        # Call token0() function
        token0_hex = call_rpc("eth_call", [
            {"to": pool_address, "data": FUNC_TOKEN0},
            "latest"
        ])

        # Call token1() function
        token1_hex = call_rpc("eth_call", [
            {"to": pool_address, "data": FUNC_TOKEN1},
            "latest"
        ])

        # Validate responses
        if not token0_hex or not token1_hex:
            raise ValueError(f"Empty result from RPC for pool {pool_address}")

        # Extract addresses from hex response (last 40 chars = 20 bytes = address)
        token0 = "0x" + token0_hex[-40:]
        token1 = "0x" + token1_hex[-40:]

        # Normalize to lowercase
        token0 = token0.lower()
        token1 = token1.lower()

        logger.info("rpc", f"Resolved pool tokens via RPC", {
            "pool": pool_address,
            "token0": token0,
            "token1": token1
        })

        return token0, token1

    except ValueError as e:
        logger.error("rpc", f"Invalid RPC response for pool {pool_address}", error=e)
        raise

    except Exception as e:
        logger.error("rpc", f"Failed to fetch pool tokens for {pool_address}", error=e)
        raise