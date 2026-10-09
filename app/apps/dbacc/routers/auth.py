"""Auth DB Accounting — DITULIS ULANG TOTAL untuk unified-backend.

Perbedaan vs aslinya (DB Acounting/backend/app/routers/auth.py):
- Hash SHA-256 + token dummy "dev-token" + header X-Tier DIHAPUS.
- Login memakai bcrypt (app.core.security.verify_password) dan mengembalikan
  JWT asli (klaim app="dbacc").
- POST /auth/register hanya diizinkan bila tabel users masih kosong (bootstrap);
  selebihnya 403. User yang dibuat selalu tier 0.
- Bentuk response dipertahankan: {token, tier, name, email}.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db

from .. import models, schemas
from ..access import APP_CLAIM, current_tier, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_out(user: models.User) -> dict:
    token = security.create_access_token(app=APP_CLAIM, sub=str(user.id), tier=user.tier)
    return {"token": token, "tier": user.tier, "name": user.name, "email": user.email}


@router.post("/register", response_model=schemas.AuthOut)
def register(body: schemas.RegisterIn, db: Session = Depends(get_db)):
    # Bootstrap saja: tolak bila sudah ada user.
    if db.query(models.User).count() > 0:
        raise HTTPException(status_code=403, detail="Registrasi ditutup — user sudah ada")
    exists = db.query(models.User).filter(models.User.email == body.email.lower()).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    user = models.User(
        name=body.name,
        email=body.email.lower(),
        password_hash=security.hash_password(body.password),
        tier=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_out(user)


@router.post("/login", response_model=schemas.AuthOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email.lower()).first()
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    return _auth_out(user)


@router.get("/me")
def me(tier_def: dict = Depends(current_tier)):
    # Satu-satunya sumber konfigurasi tier untuk frontend: dihitung server
    # dari tier user di DB (bukan dari input client). Bentuk lama {tier, menus}
    # dipertahankan; name/roleLabel/permissions ditambah agar frontend tidak
    # perlu lagi salinan file tier lokal.
    return {
        "tier": tier_def["tier"],
        "name": tier_def.get("name"),
        "roleLabel": tier_def.get("roleLabel"),
        "description": tier_def.get("description"),
        "menus": tier_def["menus"],
        "permissions": tier_def.get("permissions", {}),
    }


@router.post("/profile")
def save_profile(body: dict, user: models.User = Depends(get_current_user)):
    return {"ok": True, "tier": user.tier}


@router.put("/password")
def change_password(body: schemas.PasswordChange, user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Ganti password sendiri. Verifikasi password lama; tolak bila sama."""
    if not security.verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password saat ini salah")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="Password baru harus berbeda")
    user.password_hash = security.hash_password(body.new_password)
    db.add(user)
    db.commit()
    return {"ok": True}
