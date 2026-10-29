# services/monero_service.py
import httpx
from fastapi import HTTPException
from real_time_auction.config import settings

# Typically runs locally on port 18082
MONERO_RPC_URL = "http://127.0.0.1:18082/json_rpc"


async def create_auction_subaddress(bid_id: int) -> dict:
    """Generate a unique subaddress for a specific won bid using account indexes."""
    async with httpx.AsyncClient() as client:
        try:
            # 1. Create a new account in the wallet for this auction item/bid
            account_payload = {
                "jsonrpc": "2.0",
                "id": "0",
                "method": "create_account",
                "params": {"label": f"Bid-{bid_id}"}
            }
            res = await client.post(MONERO_RPC_URL, json=account_payload, timeout=10.0)
            data = res.json()

            if "result" not in data:
                raise HTTPException(status_code=500, detail=f"Monero RPC error: {data}")

            account_index = data["result"]["account_index"]

            # 2. Get the primary subaddress for this new account
            addr_payload = {
                "jsonrpc": "2.0",
                "id": "0",
                "method": "get_address",
                "params": {"account_index": account_index}
            }
            addr_res = await client.post(MONERO_RPC_URL, json=addr_payload, timeout=10.0)
            addr_data = addr_res.json()

            return {
                "subaddress": addr_data["result"]["address"],
                "address_index": account_index
            }
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Failed to connect to Monero wallet daemon: {exc}")


async def get_subaddress_balance(address_index: int) -> float:
    """Check received balance for the specific account index."""
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": "0",
                "method": "get_balance",
                "params": {"account_index": address_index}
            }
            res = await client.post(MONERO_RPC_URL, json=payload, timeout=10.0)
            data = res.json()

            if "result" in data:
                # Monero returns balance in atomic units (piconero: 1 XMR = 10^12 piconero)
                return data["result"].get("balance", 0) / 1e12
            return 0.0
        except Exception:
            return 0.0
