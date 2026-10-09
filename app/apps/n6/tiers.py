from __future__ import annotations
"""Porting dari N6/backend/app/core/tiers.py.

Matriks akses, dimuat dari ``app/apps/n6/tiers/*.json``.

Satu file JSON per tier di atas owner:

    tier-1-admin.json       Admin CS
    tier-2-headcoach.json   Head Coach
    tier-3-coach.json       Coach
    tier-4-client.json      Client

Tidak ada ``tier-0-owner.json``: owner adalah kasus "melihat semuanya" yang
implisit; menambah file hanya membuat keduanya bisa drift.

Aturannya, identik di kedua sisi kabel:

    a user at tier T may use any feature whose tier is >= T

Perubahan vs aslinya: TIERS_DIR default mengarah ke folder ``tiers/`` di
samping file ini (bukan settings.TIERS_DIR); import settings dihapus.
Semantik enforcement dipertahankan persis.
"""


import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# Tier numbers are part of the contract with js/core/registry.js::TIER and with
# the tier JSON filenames. Do not renumber.
TIER_OWNER = 0
TIER_ADMIN = 1
TIER_HEADCOACH = 2
TIER_COACH = 3
TIER_CLIENT = 4

TIER_MAX = TIER_CLIENT

#: tier -> role key, used to map an account's tier back onto a role.
ROLE_BY_TIER: dict[int, str] = {
    TIER_ADMIN: "admin",
    TIER_HEADCOACH: "headcoach",
    TIER_COACH: "coach",
    TIER_CLIENT: "client",
}

#: Folder tier milik aplikasi ini (disalin apa adanya dari N6/backend/tiers/).
TIERS_DIR = Path(__file__).resolve().parent / "tiers"

_CACHE: dict[int, "Tier"] = {}
_LOCK = threading.Lock()


@dataclass(frozen=True)
class Tier:
    """One parsed ``tier-*.json`` file."""

    tier: int
    role: str
    label: str
    description: str = ""
    inherits: tuple[int, ...] = ()
    rule: str = ""
    menus: frozenset[str] = frozenset()
    actions: dict[str, frozenset[str]] = field(default_factory=dict)
    endpoints: dict[str, tuple[str, ...]] = field(default_factory=dict)
    source: str = ""

    # ---------------------------------------------------------------- queries
    def has_menu(self, menu_key: str) -> bool:
        return menu_key in self.menus

    def has_action(self, domain: str, action: str) -> bool:
        return action in self.actions.get(domain, frozenset())

    @property
    def allowed_endpoint_patterns(self) -> tuple[str, ...]:
        return self.endpoints.get("allow", ())

    @property
    def denied_endpoint_patterns(self) -> tuple[str, ...]:
        return self.endpoints.get("deny", ())

    def summary(self) -> dict[str, Any]:
        """Shape returned to the browser by GET /auth/me and GET /auth/tiers."""
        return {
            "tier": self.tier,
            "role": self.role,
            "label": self.label,
            "description": self.description,
            "rule": self.rule,
            "menus": sorted(self.menus),
            "actions": {d: sorted(a) for d, a in sorted(self.actions.items())},
        }


def _tier_files(directory: Path | None = None) -> Iterable[Path]:
    root = Path(directory or TIERS_DIR)
    if not root.is_dir():
        return []
    return sorted(root.glob("tier-*.json"))


def _parse(path: Path) -> Tier:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "tier" not in raw:
        raise ValueError(f"{path.name}: missing 'tier'")

    actions: dict[str, frozenset[str]] = {}
    for domain, allowed in (raw.get("actions") or {}).items():
        if not isinstance(allowed, list):
            raise ValueError(f"{path.name}: actions.{domain} must be a list")
        actions[str(domain)] = frozenset(str(a) for a in allowed)

    endpoints: dict[str, tuple[str, ...]] = {}
    for bucket, entries in (raw.get("endpoints") or {}).items():
        if not isinstance(entries, list):
            raise ValueError(f"{path.name}: endpoints.{bucket} must be a list")
        endpoints[str(bucket)] = tuple(str(e) for e in entries)

    return Tier(
        tier=int(raw["tier"]),
        role=str(raw.get("role") or ""),
        label=str(raw.get("label") or path.stem),
        description=str(raw.get("description") or ""),
        inherits=tuple(int(i) for i in (raw.get("inherits") or [])),
        rule=str(raw.get("rule") or ""),
        menus=frozenset(str(m) for m in (raw.get("menus") or [])),
        actions=actions,
        endpoints=endpoints,
        source=path.name,
    )


def load_tiers(directory: Path | None = None, *, refresh: bool = False) -> dict[int, Tier]:
    """
    Read every ``tier-*.json`` and return ``{tier_number: Tier}``.

    Cached after the first call; pass ``refresh=True`` after editing a file.
    """
    with _LOCK:
        if _CACHE and not refresh and directory is None:
            return dict(_CACHE)

        parsed: dict[int, Tier] = {}
        problems: list[str] = []
        for path in _tier_files(directory):
            try:
                tier = _parse(path)
            except (ValueError, json.JSONDecodeError) as exc:
                problems.append(f"{path.name}: {exc}")
                continue
            if tier.tier <= TIER_OWNER:
                problems.append(
                    f"{path.name}: tier {tier.tier} needs no file; owner is the implicit all-access case"
                )
                continue
            if tier.tier > TIER_MAX:
                problems.append(f"{path.name}: tier {tier.tier} is outside the ladder 0..{TIER_MAX}")
                continue
            if tier.tier in parsed:
                problems.append(f"{path.name}: tier {tier.tier} already defined by {parsed[tier.tier].source}")
                continue
            parsed[tier.tier] = tier

        missing = [t for t in range(TIER_ADMIN, TIER_MAX + 1) if t not in parsed]
        if missing:
            problems.append(f"missing tier files for {missing} in {directory or TIERS_DIR}")

        if problems:
            raise RuntimeError("tier matrix is invalid: " + "; ".join(problems))

        if directory is None:
            _CACHE.clear()
            _CACHE.update(parsed)
        return dict(parsed)


def get_tier_matrix(*, refresh: bool = False) -> dict[int, Tier]:
    return load_tiers(refresh=refresh)


def tier_matrix_for(tier: int) -> Tier | None:
    """
    Matrix for one tier.

    Tier 0 (owner) has no file and therefore no restrictions: this returns
    ``None`` on purpose, so every caller is forced through the is_owner()
    branch rather than silently inheriting some other tier's limits.
    """
    return load_tiers().get(int(tier))


def is_owner(tier: int | None) -> bool:
    return tier is not None and int(tier) == TIER_OWNER


def can_access_menu(tier: int | None, menu_key: str) -> bool:
    """May a user at ``tier`` open this menu? Owner: always."""
    if is_owner(tier):
        return True
    matrix = tier_matrix_for(tier) if tier is not None else None
    return bool(matrix and matrix.has_menu(menu_key))


def can_perform(tier: int | None, domain: str, action: str) -> bool:
    """May a user at ``tier`` do ``action`` on ``domain``? Owner: always."""
    if is_owner(tier):
        return True
    matrix = tier_matrix_for(tier) if tier is not None else None
    return bool(matrix and matrix.has_action(domain, action))


def available_menus(tier: int | None) -> frozenset[str]:
    if is_owner(tier):
        raise ValueError("owner has no tier file; use the frontend catalogue instead")
    matrix = tier_matrix_for(tier) if tier is not None else None
    return matrix.menus if matrix else frozenset()


def available_actions(tier: int | None) -> dict[str, frozenset[str]]:
    if is_owner(tier):
        raise ValueError("owner has no tier file; use the frontend catalogue instead")
    matrix = tier_matrix_for(tier) if tier is not None else None
    return dict(matrix.actions) if matrix else {}


def role_for_tier(tier: int | None) -> str:
    """'owner' for tier 0, otherwise the role key from the tier file."""
    if is_owner(tier):
        return "owner"
    matrix = tier_matrix_for(tier) if tier is not None else None
    return matrix.role if matrix else "client"
