from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.claisrox.access import load_tiers, menus_for_tier
from app.apps.claisrox.deps import get_current_user
from app.apps.claisrox.models import User
from app.apps.claisrox.schemas.auth import LoginRequest, SessionResponse, TokenResponse
from app.core import security
from app.core.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not user.is_active or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Username atau password salah")
    token = security.create_access_token(app="claisrox", sub=str(user.id), tier=user.tier)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=SessionResponse)
def me(user: User = Depends(get_current_user)):
    # Hak akses dihitung server dari tier user (file tiers/tier_N.json).
    tier_name = load_tiers().get(user.tier, {}).get("name", "")
    return SessionResponse(
        username=user.username,
        name=user.name,
        tier=user.tier,
        tier_name=tier_name,
        menus=menus_for_tier(user.tier),
    )


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


@router.put("/password")
def change_password(
    body: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ganti password sendiri. Berlaku untuk semua tier yang sudah login."""
    if not security.verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password saat ini salah")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password baru harus berbeda")
    user.password_hash = security.hash_password(body.new_password)
    db.commit()
    return {"ok": True, "detail": "Password berhasil diganti"}
