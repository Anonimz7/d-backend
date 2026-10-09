"""Login + info user + file tier."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import security as core_security
from app.core.database import get_db

from ..access import load_tier
from ..models import User
from ..security import APP_CLAIM, get_current_user

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not core_security.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Username atau password salah")
    return {
        "access_token": core_security.create_access_token(
            app=APP_CLAIM, sub=str(user.id), tier=user.tier
        ),
        "token_type": "bearer",
        "tier": user.tier,
        "user": {"name": user.name, "role": user.role},
    }


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "role": user.role, "tier": user.tier}


@router.get("/access/me")
def my_access(user: User = Depends(get_current_user)):
    """Hak akses user ini: {tier, name, menus, features}.

    Dihitung server dari kolom tier user di DB (bukan dari input client).
    Frontend memakai ini sebagai satu-satunya sumber konfigurasi tier.
    """
    tier_def = load_tier(user.tier)
    return {
        "tier": user.tier,
        "name": tier_def.get("name"),
        "menus": tier_def.get("menus", {}),
        "features": tier_def.get("features", {}),
    }


@router.get("/tiers/{n}")
def get_tier(n: int, user: User = Depends(get_current_user)):
    # Tier yang lebih kecil (lebih tinggi hak aksesnya) boleh melihat tier lain; selain itu hanya tier sendiri.
    if n < user.tier:
        raise HTTPException(403, "Tidak boleh melihat tier ini")
    return load_tier(n)


class PasswordChange(BaseModel):
    curr_pwd: str = Field(min_length=1, max_length=256, alias="current_password")
    new_pwd: str = Field(min_length=8, max_length=256, alias="new_password")

    class Config:
        populate_by_name = True


@router.put("/auth/password")
def change_password(body: PasswordChange, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Ganti password sendiri. Berlaku untuk semua tier yang sudah login."""
    if not core_security.verify_password(body.curr_pwd, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password saat ini salah")
    if body.curr_pwd == body.new_pwd:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password baru harus berbeda")
    user.password_hash = core_security.hash_password(body.new_pwd)
    db.commit()
    return {"ok": True, "detail": "Password berhasil diganti"}
