# NEWS — headlines, whales (dark pool), SEC filings (register /whales and /sec before /{symbol})
from fastapi import APIRouter

router = APIRouter()


@router.get("/whales/{symbol}", summary="Dark pool prints")
async def get_news_whales(symbol: str):
    return {"symbol": symbol, "whales": []}


@router.get("/sec/{symbol}", summary="Recent SEC filings")
async def get_news_sec(symbol: str):
    return {"symbol": symbol, "filings": []}


@router.get("/{symbol}", summary="Latest headlines for symbol")
async def get_news(symbol: str):
    return {"symbol": symbol, "headlines": []}
