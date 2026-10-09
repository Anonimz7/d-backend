from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db

from .. import models, schemas
from ..deps import current_user
from ..services.access import keys_for_tier

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.username == body.username))
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Username atau password salah")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Akun dinonaktifkan")
    return schemas.TokenOut(
        access_token=security.create_access_token(app="dbfin", sub=str(user.id), tier=user.tier),
        tier=user.tier,
    )


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


@router.put("/auth/password")
def change_password(
    body: PasswordChange,
    db: Session = Depends(get_db),
    user: models.User = Depends(current_user),
):
    """Ganti password sendiri. Membutuhkan password saat ini yang benar."""
    if not security.verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password saat ini salah")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password baru harus berbeda")
    user.password_hash = security.hash_password(body.new_password)
    db.commit()
    return {"ok": True}


@router.get("/access/me", response_model=schemas.AccessOut)
def my_access(user: models.User = Depends(current_user)):
    return schemas.AccessOut(tier=user.tier, name=user.name, access=keys_for_tier(user.tier))
