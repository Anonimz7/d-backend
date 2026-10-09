from __future__ import annotations
"""POST /auth/login, /auth/refresh, /auth/logout, PUT /auth/password, GET /auth/me."""

"""Porting dari N6/backend/app/api/v1/endpoints/auth.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core import security
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("n6.auth")
from ..tiers import TIER_ADMIN, TIER_MAX, TIER_OWNER, is_owner, tier_matrix_for
from ..models import Account
from ..schemas.auth import (
    LoginRequest,
    PasswordChange,
    RefreshRequest,
    TokenPair,
    UserProfile,
)
from ..schemas.common import Ok
from ..deps import CurrentPrincipal, DbSession, touch_last_login

router = APIRouter(prefix="/auth", tags=["auth"])

# Router terpisah agar path final = /api/n6/v1/access/me (seragam lintas aplikasi).
access_router = APIRouter(prefix="/access", tags=["auth"])


def _profile(account: Account) -> UserProfile:
    """Build the /auth/me payload, echoing the server's own access matrix."""
    matrix = None if is_owner(account.tier) else tier_matrix_for(account.tier)
    if matrix is None:
        menus: list[str] = []
        actions: dict[str, list[str]] = {}
    else:
        menus = sorted(matrix.menus)
        actions = {d: sorted(a) for d, a in matrix.actions.items()}

    return UserProfile(
        id=account.id,
        username=account.username,
        full_name=account.full_name,
        email=account.email,
        tier=account.tier,
        role="owner" if is_owner(account.tier) else matrix.role,
        is_active=account.is_active,
        client_id=account.client_id,
        coach_id=account.coach_id,
        last_login_at=account.last_login_at,
        menus=menus,
        actions=actions,
    )


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Exchange credentials for an access + refresh token pair",
)
def login(payload: LoginRequest, db: DbSession) -> TokenPair:
    account = db.scalar(
        select(Account).where(func.lower(Account.username) == payload.username.strip().lower())
    )
    if account is None or not security.verify_password(payload.password, account.password_hash):
        # One message for both cases: do not confirm which usernames exist.
        logger.warning("login gagal: %s", payload.username.strip())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username or password is incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    touch_last_login(db, account)
    db.commit()
    db.refresh(account)
    logger.info("login berhasil: %s (tier %s)", account.username, account.tier)

    # ADAPTASI unified-backend: klaim app="n6" wajib; klaim "username" tidak
    # didukung app.core.security (tidak pernah dibaca server).
    access_token = security.create_access_token(
        app="n6", sub=str(account.id), tier=int(account.tier)
    )
    refresh_token = security.create_refresh_token(app="n6", sub=str(account.id))
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenPair, summary="Mint a new access token")
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        claims = security.decode_token(payload.refresh_token, app="n6", expect_typ="refresh")
    except security.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    account = db.get(Account, int(claims["sub"]))
    if account is None or not account.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is unavailable")

    # ADAPTASI unified-backend: lihat login di atas.
    access_token = security.create_access_token(
        app="n6", sub=str(account.id), tier=int(account.tier)
    )
    refresh_token = security.create_refresh_token(app="n6", sub=str(account.id))
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=Ok, summary="Sign out")
def logout(principal: CurrentPrincipal) -> Ok:
    """
    Tokens are stateless, so this only tells the client to drop them.

    No `require(...)` here on purpose: signing out has to work for every tier,
    including a client, whose `accounts` action list is empty. Authentication
    via `principal` is still required, so an anonymous caller gets a 401 rather
    than a free no-op.

    To make sign-out revoke access immediately, keep a deny list of `jti`
    values here and check it in get_principal.
    """
    return Ok(detail="Drop the stored tokens on the client.")


@router.get("/me", response_model=UserProfile, summary="Who am I, and what may I open")
def me(principal: CurrentPrincipal) -> UserProfile:
    return _profile(principal.account)


@access_router.get("/me", response_model=UserProfile, summary="My access, from the server's tier matrix")
def access_me(principal: CurrentPrincipal) -> UserProfile:
    """Alias seragam lintas aplikasi untuk /auth/me.

    Mengembalikan profil + menus/actions user ini, dihitung server dari
    tier di DB (bukan dari input client). Frontend memakai ini sebagai
    satu-satunya sumber konfigurasi tier.
    """
    return _profile(principal.account)


@router.put("/password", response_model=Ok, summary="Change your own password")
def change_password(
    payload: PasswordChange,
    db: DbSession,
    principal: CurrentPrincipal,
) -> Ok:
    account = principal.account
    if not security.verify_password(payload.current_password, account.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")

    account.password_hash = security.hash_password(payload.new_password)
    account.updated_at = datetime.now(timezone.utc)
    db.add(account)
    db.commit()
    return Ok(detail="Password updated. Existing tokens stay valid until they expire.")


@router.get("/tiers", summary="The access matrix this server is enforcing")
def tiers(principal: CurrentPrincipal) -> dict:
    """
    Introspection endpoint: which menus and actions this token carries.

    Tier 0 is `null` in the `tiers` map, and `you.menus`/`you.actions` come
    back empty because owner is the implicit all-access case. That emptiness is
    the machine-readable form of "there is no tier-0-owner.json".
    """
    ladder = [TIER_OWNER, TIER_ADMIN, 2, 3, TIER_MAX]
    matrix = {
        str(tier): (m.summary() if (m := tier_matrix_for(tier)) is not None else None)
        for tier in ladder
    }
    return {
        "ladder": ladder,
        "rule": "a user at tier T may use any feature whose tier is >= T",
        "you": _profile(principal.account).model_dump(mode="json"),
        "tiers": matrix,
    }