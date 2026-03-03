# MONITOR — pnl, equity-curve, drawdown, metrics, tca
from fastapi import APIRouter

router = APIRouter()


@router.get("/pnl", summary="Today PnL, realized, unrealized")
async def get_pnl():
    return {"today_pnl": 0, "realized": 0, "unrealized": 0}


@router.get("/equity-curve", summary="Equity curve, daily PnL and CB events")
async def get_equity_curve():
    # Stub: 30-day equity curve with flat values and no events
    curve = [
        {"date": f"2025-01-{day:02d}", "equity": 10000 + day * 10}
        for day in range(1, 31)
    ]
    daily = [
        {"date": point["date"], "pnl": point["equity"] - curve[0]["equity"]}
        for point in curve
    ]
    cb_events = []
    return {"curve": curve, "daily": daily, "cb_events": cb_events}


@router.get("/drawdown", summary="Current DD, limit, circuit breaker")
async def get_drawdown():
    return {"current_pct": 0, "limit_pct": 1.5, "cb_fired": False}


@router.get("/metrics", summary="Sharpe, win rate, avg win/loss")
async def get_metrics():
    return {"sharpe": 0, "win_rate": 0, "avg_win": 0, "avg_loss": 0}


@router.get("/tca", summary="Transaction cost analysis summary")
async def get_tca():
    return {"summary": {}}
