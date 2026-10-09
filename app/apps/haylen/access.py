"""Akses berbasis tier. Aturan akses dibaca dari app/apps/haylen/tiers/tier{n}.json.

Tier 0 = Owner (semua fitur), 1 = Admin, 2 = Coach, 3 = cadangan.
Level: none < view < limited < manage < full
  view    -> hanya GET
  limited -> GET, POST, PUT
  manage/full -> GET, POST, PUT, DELETE
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, HTTPException, status

from .models import User
from .security import get_current_user

TIER_DIR = Path(__file__).resolve().parent / "tiers"
LEVELS = {"none": 0, "view": 1, "limited": 2, "manage": 3, "full": 4}
NEEDED = {"GET": 1, "POST": 2, "PUT": 2, "PATCH": 2, "DELETE": 3}


@lru_cache(maxsize=8)
def load_tier(n: int) -> dict:
    path = TIER_DIR / f"tier{n}.json"
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tier {n} tidak ada")
    return json.loads(path.read_text(encoding="utf-8"))


def level_of(user: User, menu: str) -> str:
    return load_tier(user.tier)["menus"].get(menu, "none")


def feature_of(user: User, feature: str) -> str:
    return load_tier(user.tier)["features"].get(feature, "none")


def require_menu(menu: str, method: str = "GET"):
    """Dependency: pastikan tier user cukup untuk menu + aksi (method HTTP)."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if LEVELS[level_of(user, menu)] < NEEDED[method]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tier Anda tidak punya akses")
        return user

    return checker
