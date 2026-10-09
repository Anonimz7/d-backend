from __future__ import annotations
"""Sign-in, tokens and the current-user profile."""


from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Disalin dari N6 core.security (batas bawah panjang password di request).
MIN_PASSWORD_LENGTH = 8
from .common import ORMModel


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)


class TokenPair(BaseModel):
    """Matches what js/core/api.js stores under CONFIG.API_TOKEN_KEY."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime in seconds")


class UserProfile(ORMModel):
    """
    Returned by GET /auth/me.

    `menus` and `actions` are the same matrix js/core/access.js enforces in the
    browser, echoed back from the server's own copy, so the two can be
    compared at runtime instead of trusted separately.
    """

    id: int
    username: str
    full_name: str
    email: str | None = None
    tier: int
    role: str
    is_active: bool = True
    client_id: int | None = None
    coach_id: int | None = None
    last_login_at: datetime | None = None
    menus: list[str] = Field(default_factory=list)
    actions: dict[str, list[str]] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": {
        "id": 1,
        "username": "admin",
        "full_name": "Admin CS",
        "tier": 1,
        "role": "admin",
        "is_active": True,
        "menus": ["beranda", "klien", "jadwalklien", "jadwalcoach", "harga", "tiket", "pesan"],
        "actions": {"clients": ["view", "create", "update", "archive", "export"]},
    }})