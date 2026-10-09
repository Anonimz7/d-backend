"""Penjagaan akses tier + identitas user via JWT.

Adaptasi dari DB Acounting/backend/app/auth.py:
- TIERS_DIR → folder tiers/ milik aplikasi ini (salinan tier-{n}.json).
- Header X-Tier DIHAPUS. Identitas diambil dari Bearer JWT (klaim app="dbacc"),
  tier dibaca dari kolom user di DB (bukan dari token).
- require_menu / require_perm dipertahankan sebagai Depends dengan semantik sama.
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db

from . import models

TIERS_DIR = Path(__file__).resolve().parent / "tiers"

bearer_scheme = HTTPBearer(auto_error=False)

APP_CLAIM = "dbacc"


@lru_cache(maxsize=8)
def load_tier(tier: int) -> dict:
    path = TIERS_DIR / f"tier-{tier}.json"
    if not path.exists():
        raise HTTPException(status_code=403, detail=f"Tier {tier} tidak dikenal")
    return json.loads(path.read_text(encoding="utf-8"))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Muat user dari Bearer token. 401 bila token hilang/tidak valid."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Token tidak ditemukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = security.decode_token(credentials.credentials, app=APP_CLAIM)
    except security.TokenError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    user = db.query(models.User).filter(models.User.id == str(payload.get("sub"))).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User tidak ditemukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def current_tier(user: models.User = Depends(get_current_user)) -> dict:
    tier = user.tier
    if tier is None or tier < 0 or tier > 3:
        raise HTTPException(status_code=403, detail="Tier tidak valid")
    return load_tier(tier)


def require_menu(menu: str):
    def guard(tier_def: dict = Depends(current_tier)) -> dict:
        if menu not in tier_def.get("menus", []):
            raise HTTPException(
                status_code=403,
                detail=f"Tier {tier_def.get('tier')} tidak boleh mengakses menu '{menu}'",
            )
        return tier_def

    return guard


def require_perm(perm: str):
    def guard(tier_def: dict = Depends(current_tier)) -> dict:
        if not tier_def.get("permissions", {}).get(perm, False):
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{perm}' ditolak untuk tier {tier_def.get('tier')}",
            )
        return tier_def

    return guard
