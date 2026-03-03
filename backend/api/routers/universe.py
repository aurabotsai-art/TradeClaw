# UNIVERSE — list, add, remove, snapshot per symbol
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AddSymbolBody(BaseModel):
    symbol: str
    asset_class: str | None = None


@router.get("", summary="Current symbol universe")
async def get_universe():
    # Stub: empty universe; wire to storage later
    return {"symbols": []}


@router.post("", summary="Add symbol")
async def post_universe(body: AddSymbolBody):
    return {"symbol": body.symbol, "asset_class": body.asset_class, "added": True}


@router.delete("/{symbol}", summary="Remove symbol")
async def delete_universe(symbol: str):
    return {"symbol": symbol, "removed": True}


@router.get("/{symbol}/snapshot", summary="OHLCV + price + headlines + agent history")
async def get_universe_snapshot(symbol: str):
    return {
        "symbol": symbol,
        "ohlcv": {},
        "price": None,
        "headlines": [],
        "agent_history": [],
    }


@router.get("/candidates", summary="Universe scanner candidates (auto-scanner)")
async def get_universe_candidates():
    # Stub: no candidates yet
    return {"candidates": []}
