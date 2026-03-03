# UI-1.2 Authentication Middleware — validate Supabase JWT on every request
import os

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Public routes: no JWT required
PUBLIC_ROUTES = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
    "/api/auth/logout",
    "/ws/prices",
    "/ws/logs",
    "/ws/state",
}


def _get_supabase_client():
    """Lazy Supabase client; returns None if not configured."""
    url = os.getenv("SUPABASE_URL", "").strip()
    key = (
        os.getenv("SUPABASE_KEY", "").strip()
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
    )
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


async def verify_jwt(request: Request, call_next):
    if request.url.path in PUBLIC_ROUTES:
        return await call_next(request)

    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    supabase = _get_supabase_client()
    if supabase is None:
        # Supabase not configured: skip verification (e.g. local dev)
        request.state.user = None
        return await call_next(request)

    try:
        user = supabase.auth.get_user(jwt=token)
        request.state.user = user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that runs verify_jwt before each request."""

    async def dispatch(self, request: Request, call_next):
        return await verify_jwt(request, call_next)
