# BACKTEST — run async, status, results, regimes
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class BacktestRunBody(BaseModel):
    regime: str | None = None
    symbol: str | None = None
    start: str | None = None
    end: str | None = None


@router.post("/run", summary="Run backtest async")
async def post_backtest_run(body: BacktestRunBody):
    return {"id": "stub-backtest-id", "status": "queued"}


@router.get("/status/{id}", summary="Check if backtest complete")
async def get_backtest_status(id: str):
    return {"id": id, "complete": False, "status": "pending"}


@router.get("/results/{id}", summary="Return, sharpe, max_dd, win_rate")
async def get_backtest_results(id: str):
    return {"return": 0, "sharpe": 0, "max_dd": 0, "win_rate": 0}


@router.get("/regimes", summary="List of saved RegimeTest results")
async def get_regimes():
    return {"regimes": []}
