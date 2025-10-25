import requests
from app.config.config import config
from app.utils.logger import logger

FUNC_TOKEN0 = "0x0dfe1681"
FUNC_TOKEN1 = "0xd21220a7"


def call_rpc(method: str, params: list):
    """
    Sends a json rpc to the official monad rpc endpoint.
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
            raise ValueError(result["error"].get("message", "Unknown RPC error"))
        return result["result"]
    except Exception as e:
        logger.error("rpc", f"RPC call failed: {method}", error=e, context={"params": params})
        raise


def get_pool_tokens(pool_address: str) -> tuple[str, str]:
    """
    gets the tokens of a pool via Monad RPC.
    """
    pool_address = pool_address.lower()

    try:
        token0_hex = call_rpc("eth_call", [{"to": pool_address, "data": FUNC_TOKEN0}, "latest"])
        token1_hex = call_rpc("eth_call", [{"to": pool_address, "data": FUNC_TOKEN1}, "latest"])

        if not token0_hex or not token1_hex:
            raise ValueError("Empty result from RPC")

        token0 = "0x" + token0_hex[-40:]
        token1 = "0x" + token1_hex[-40:]

        logger.info("evm", f"Resolved pool tokens via Monad RPC", {"pool": pool_address, "token0": token0, "token1": token1})
        return token0.lower(), token1.lower()

    except Exception as e:
        logger.error("evm", f"Failed to fetch pool tokens for {pool_address}", error=e)
        raise
