from __future__ import annotations
"""Account administration. Tier changes are owner-only (see deps.require)."""


from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Disalin dari N6 core.security (batas bawah panjang password di request).
MIN_PASSWORD_LENGTH = 8
from ..tiers import TIER_ADMIN, TIER_MAX, TIER_OWNER
from .common import ORMModel


class AccountCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    tier: int = Field(default=TIER_MAX, ge=TIER_OWNER, le=TIER_MAX)
    client_id: int | None = None
    coach_id: int | None = None
    is_active: bool = True

    @field_validator("tier")
    @classmethod
    def _tier_in_range(cls, v: int) -> int:
        # Tier 0 has no JSON file: it is the implicit all-access case. Creating
        # an owner through this endpoint would bypass that intent.
        if v == TIER_OWNER:
            raise ValueError("tier 0 (owner) accounts are created by bootstrap, not through this API")
        return v


class AccountPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    client_id: int | None = None
    coach_id: int | None = None


class TierChange(BaseModel):
    """PUT /accounts/{id}/tier"""

    tier: int = Field(ge=TIER_ADMIN, le=TIER_MAX)
    reason: str | None = Field(default=None, max_length=255)


class AccountRead(ORMModel):
    id: int
    username: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    tier: int
    is_active: bool
    client_id: int | None = None
    coach_id: int | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None