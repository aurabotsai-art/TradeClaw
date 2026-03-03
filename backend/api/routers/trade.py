# TRADE — paper/live execute, positions, orders, close position
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class TradeBody(BaseModel):
    symbol: str
    side: str
    params: dict | None = None


@router.post("/paper", summary="Execute paper trade")
async def post_trade_paper(body: TradeBody):
    return {"order_id": "stub", "symbol": body.symbol, "side": body.side, "mode": "paper"}


@router.post("/live", summary="Execute live trade (gated)")
async def post_trade_live(body: TradeBody):
    return {"order_id": "stub", "symbol": body.symbol, "side": body.side, "mode": "live"}


@router.get("/positions", summary="All open positions from Alpaca")
async def get_positions():
    return {"positions": []}


@router.get("/orders", summary="Recent orders")
async def get_orders():
    return {"orders": []}


@router.delete("/position/{symbol}", summary="Close a position")
async def delete_position(symbol: str):
    return {"symbol": symbol, "closed": True}
