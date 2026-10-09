"""Hak akses menu per tier. Sumber kebenaran: file JSON di tiers/ (satu file per tier).

Tier 0 (owner) memakai wildcard "*" sehingga otomatis mencakup menu baru.
"""
import json
from functools import lru_cache
from pathlib import Path

TIERS_DIR = Path(__file__).parent / "tiers"
WILDCARD = "*"

# Dashboard & laporan merangkum semua data, jadi pemegangnya boleh MEMBACA seluruh koleksi.
READ_ALL_MENUS = frozenset({"dashboard", "laporan"})


@lru_cache
def load_tiers() -> dict[int, dict]:
    tiers = {}
    for path in sorted(TIERS_DIR.glob("tier_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        tiers[data["tier"]] = data
    return tiers


def menus_for_tier(tier: int) -> list[str]:
    return list(load_tiers().get(tier, {}).get("menus", []))


def can_access(tier: int, menu: str) -> bool:
    menus = menus_for_tier(tier)
    return WILDCARD in menus or menu in menus


def can_read_all(tier: int) -> bool:
    return any(can_access(tier, menu) for menu in READ_ALL_MENUS)
