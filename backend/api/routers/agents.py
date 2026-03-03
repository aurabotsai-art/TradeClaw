# AGENTS — last-run, weights, run-consensus
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RunConsensusBody(BaseModel):
    symbol: str


@router.get("/last-run", summary="Last consensus run results (all 4 agents)")
async def get_last_run():
    return {"agents": [], "consensus": None, "status": "ok"}


@router.get("/weights", summary="Current agent IC weights")
async def get_weights():
    return {"weights": {}}


@router.post("/run-consensus", summary="Trigger consensus manually")
async def post_run_consensus(body: RunConsensusBody):
    return {"symbol": body.symbol, "status": "triggered"}
