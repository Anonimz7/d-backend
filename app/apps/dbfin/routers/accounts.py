"""Kelola akun user DB Finance (owner only) + daftar untuk UI Kelola Anggota.

- GET    /accounts            daftar user (paginasi sederhana)
- POST   /accounts            tambah user; tier default = 3 (paling bawah)
- PATCH  /accounts/{id}       ubah nama/aktif
- PUT    /accounts/{id}/tier  ubah tier (1..3; tier 0 tidak bisa diberikan/dicabut via API)
- DELETE /accounts/{id}       nonaktifkan user (is_active=False)

Semua endpoint owner-only (tier == 0). Tier diambil dari kolom DB user login,
bukan dari klaim token.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import security as core_security
from app.core.database import get_db

from ..deps import current_user
from ..models import User

router = APIRouter(tags=["accounts"])

TIER_OWNER = 0
TIER_MIN_ASSIGNABLE = 1
TIER_DEFAULT = 3  # tier paling bawah untuk anggota baru
TIER_MAX = 3


def _require_owner(user: User) -> User:
    if user.tier != TIER_OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hanya owner")
    return user


def _user_out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "name": u.name,
        "tier": u.tier,
        "is_active": u.is_active,
    }


@router.get("/accounts")
def list_accounts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _require_owner(user)
    q = db.query(User).order_by(User.tier, User.username)
    total = q.count()
    items = [_user_out(u) for u in q.limit(limit).offset(offset).all()]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


class AccountCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    tier: int = Field(default=TIER_DEFAULT, ge=TIER_MIN_ASSIGNABLE, le=TIER_MAX)


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    body: AccountCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _require_owner(user)
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username sudah dipakai")
    u = User(
        username=body.username.strip(),
        name=body.name.strip(),
        password_hash=core_security.hash_password(body.password),
        tier=body.tier,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return _user_out(u)


class AccountPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None


@router.patch("/accounts/{account_id}")
def update_account(
    account_id: int,
    body: AccountPatch,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _require_owner(user)
    u = db.get(User, account_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User tidak ditemukan")
    if u.id == user.id and body.is_active is False:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tidak bisa menonaktifkan akun sendiri")
    if body.name is not None:
        u.name = body.name.strip()
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    return _user_out(u)


class TierChange(BaseModel):
    tier: int = Field(ge=TIER_MIN_ASSIGNABLE, le=TIER_MAX)


@router.put("/accounts/{account_id}/tier")
def set_tier(
    account_id: int,
    body: TierChange,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _require_owner(user)
    u = db.get(User, account_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User tidak ditemukan")
    if u.tier == TIER_OWNER:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tier owner tidak bisa diubah via API")
    u.tier = body.tier
    db.commit()
    db.refresh(u)
    return _user_out(u)


@router.delete("/accounts/{account_id}")
def deactivate_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _require_owner(user)
    u = db.get(User, account_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User tidak ditemukan")
    if u.id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tidak bisa menonaktifkan akun sendiri")
    if u.tier == TIER_OWNER:
        raise HTTPException(status.HTTP_409_CONFLICT, "Akun owner tidak bisa dinonaktifkan")
    u.is_active = False
    db.commit()
    return {"ok": True}


@router.delete("/accounts/{account_id}/hard")
def hard_delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Hapus permanen akun. Hanya owner. Tidak bisa hapus diri sendiri atau owner lain."""
    _require_owner(user)
    u = db.get(User, account_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User tidak ditemukan")
    if u.id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Tidak bisa menghapus akun sendiri")
    if u.tier == TIER_OWNER:
        raise HTTPException(status.HTTP_409_CONFLICT, "Akun owner tidak bisa dihapus")
    db.delete(u)
    db.commit()
    return {"ok": True}
