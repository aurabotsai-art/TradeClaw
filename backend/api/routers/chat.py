# UI-2.3 SSE Streaming Endpoint — session create + stream with handle_message
import json
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.orchestration.chat_orchestrator import handle_message

router = APIRouter()

# Session mode store: Redis when available, else in-memory (see _get_session_mode / _set_session_mode)
_session_modes: dict[str, str] = {}
_redis = None


def _get_redis():
    """Lazy Redis client for session state. Returns None if not configured."""
    global _redis
    if _redis is not None:
        return _redis
    import os
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        return None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(url)
        return _redis
    except Exception:
        return None


async def _get_session_mode(session_id: str) -> str:
    r = _get_redis()
    if r is None:
        return _session_modes.get(session_id) or "analysis"
    try:
        raw = await r.get(f"session:{session_id}:mode")
        return (raw.decode() if isinstance(raw, bytes) else raw) or "analysis"
    except Exception:
        return _session_modes.get(session_id) or "analysis"


async def _set_session_mode(session_id: str, mode: str) -> None:
    r = _get_redis()
    _session_modes[session_id] = mode
    if r is not None:
        try:
            await r.set(f"session:{session_id}:mode", mode)
        except Exception:
            pass


class ChatRequest(BaseModel):
    """Body for create session. Plan: body.mode or 'analysis'."""
    mode: str | None = "analysis"


@router.post("", summary="Start session, returns session_id")
async def create_chat_session(body: ChatRequest, request: Request):
    session_id = str(uuid.uuid4())
    await _set_session_mode(session_id, (body.mode or "analysis").lower())
    return {"session_id": session_id}


@router.get("/stream/{session_id}", summary="SSE stream of response tokens + tool calls")
async def stream_chat(session_id: str, message: str, request: Request):
    mode = await _get_session_mode(session_id)

    async def event_generator():
        async for event in handle_message(session_id, message, mode):
            yield f"data: {json.dumps(event)}\n\n"
            if await request.is_disconnected():
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", summary="List of past sessions from Supabase")
async def get_chat_history():
    return {"sessions": []}


@router.get("/session/{id}", summary="Full session messages")
async def get_chat_session(id: str):
    return {"session_id": id, "messages": []}
