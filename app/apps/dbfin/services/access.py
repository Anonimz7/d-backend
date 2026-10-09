"""
Hak akses berdasarkan tier (porting DB Finance).

Setiap tier punya file tier<N>.json berisi key akses (id menu). Tier N mendapat key miliknya
ditambah semua key tier di atasnya (N+1 dst), jadi tier 0 (owner) otomatis bisa semuanya.
File yang dibaca sama dengan yang dipakai frontend; path diperbaiki agar menunjuk ke
folder tiers/ milik aplikasi ini (bukan lagi "../claisrox/js/access/tiers" yang rusak).
"""
import json
import re
from functools import lru_cache
from pathlib import Path

TIERS_DIR = Path(__file__).resolve().parent.parent / "tiers"

_TIER_FILE = re.compile(r"^tier(\d+)\.json$")


@lru_cache
def _load(directory: str, signature: tuple) -> dict[int, list[str]]:
    tiers: dict[int, list[str]] = {}
    for f in Path(directory).iterdir():
        m = _TIER_FILE.match(f.name)
        if m:
            tiers[int(m.group(1))] = list(json.loads(f.read_text(encoding="utf-8"))["access"])
    return tiers


def _tiers() -> dict[int, list[str]]:
    d = TIERS_DIR
    # signature berisi mtime, sehingga perubahan file tier langsung terbaca tanpa restart
    sig = tuple(sorted((f.name, f.stat().st_mtime_ns) for f in d.glob("tier*.json")))
    if not sig:
        raise RuntimeError(f"Tidak ada file tier*.json di {d}")
    return _load(str(d), sig)


def keys_for_tier(tier: int) -> list[str]:
    tiers = _tiers()
    seen: list[str] = []
    for n in sorted(k for k in tiers if k >= tier):
        for key in tiers[n]:
            if key not in seen:
                seen.append(key)
    return seen


def max_tier() -> int:
    return max(_tiers())
