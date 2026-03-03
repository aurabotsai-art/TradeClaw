# RISK — state, correlation, kill-switch, set-params
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class KillSwitchBody(BaseModel):
    enabled: bool


class SetParamsBody(BaseModel):
    max_dd: float | None = None
    per_trade_risk: float | None = None
    atr_mult: float | None = None


@router.get("/state", summary="Full risk state (DD, CB, positions, Kelly)")
async def get_risk_state():
    return {
        "mode": "analysis",
        "dd_pct": 0,
        "cb_fired": False,
        "positions": [],
        "equity": 10000,
        "risk_per_trade": 100,
        "max_dd_limit_pct": 1.5,
        "per_trade_risk_pct": 1.0,
        "atr_mult": 2.0,
        "win_rate": 55,
        "avg_win": 50,
        "avg_loss": -40,
        "kelly_f": 0.12,
        "deployed_pct": 20,
        "corr_max": 0.4,
        "slippage": 1.2,
        "kill_switch": False,
        "kill_switch_last_toggled": None,
    }


@router.get("/correlation", summary="Correlation matrix of open positions")
async def get_risk_correlation():
    return {"matrix": []}


@router.post("/kill-switch", summary="Toggle kill switch")
async def post_kill_switch(body: KillSwitchBody):
    return {"enabled": body.enabled, "status": "ok"}


@router.post("/set-params", summary="Set max_dd, per_trade_risk, atr_mult")
async def post_set_params(body: SetParamsBody):
    return {"max_dd": body.max_dd, "per_trade_risk": body.per_trade_risk, "atr_mult": body.atr_mult}


@router.get("/post-mortem", summary="Post-mortem log of circuit breaker events")
async def get_post_mortem():
    # Stub: no events yet
    return {"events": []}


@router.get("/circuit-breakers", summary="Circuit breaker history")
async def get_circuit_breakers():
    # Stub: no events yet
    return {"events": []}
