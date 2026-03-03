# AUTH — login, logout, me (Supabase session)
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/login", summary="Supabase session")
async def post_login(body: LoginBody):
    return {"session": "stub", "user": {"email": body.email}, "access_token": "stub"}


@router.post("/logout", summary="Logout")
async def post_logout():
    return {"status": "ok"}


@router.get("/me", summary="Current user info")
async def get_me():
    return {"user": None, "status": "ok"}
