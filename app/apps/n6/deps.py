from __future__ import annotations
"""Porting dari N6/backend/app/api/deps.py.

Adaptasi: security/config/database dari app.core; decode_token memakai
klaim app="n6" (tier diambil dari DB via account.tier, bukan dari token).

Request dependencies, including the authoritative access check.

The rule everywhere in this app:

    a user at tier T may use any feature whose tier is >= T

Tier 0 is owner and reaches everything by definition, so it has no JSON file;
every other tier is described by backend/tiers/*.json.

Why this file and not js/core/access.js: the browser gate is a UX affordance.
Hiding a menu item is trivial to undo from devtools, so it must never be the
thing that decides. Every mutating route below calls ``require(domain, action)``
or ``require_menu(menu_key)``, both of which raise 403.

Tier files also carry an ``endpoints`` block with allow/deny patterns. That
block is documentation for humans and for a future gateway: enforcement is by
domain+action here, which is the same matrix the frontend uses, so the two can
never answer differently for the same question.
"""


from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from .period import PERIOD_RE, current_month
from .tiers import TIER_OWNER, can_access_menu, can_perform, is_owner, role_for_tier, tier_matrix_for
from .models import Account, Client
from app.core.database import get_db

# auto_error=False so a missing header produces our own 401 shape.
bearer_scheme = HTTPBearer(auto_error=False, description="Bearer access token")

DbSession = Annotated[Session, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


class Principal:
    """The signed-in account plus the answers it needs on every request."""

    __slots__ = ("account", "token_claims")

    def __init__(self, account: Account, token_claims: dict | None = None) -> None:
        self.account = account
        self.token_claims = token_claims or {}

    # ------------------------------------------------------------------ views
    @property
    def id(self) -> int:
        return int(self.account.id)

    @property
    def tier(self) -> int:
        return int(self.account.tier)

    @property
    def role(self) -> str:
        return role_for_tier(self.tier)

    @property
    def client_id(self) -> int | None:
        return self.account.client_id

    @property
    def coach_id(self) -> int | None:
        return self.account.coach_id

    @property
    def is_owner(self) -> bool:
        return is_owner(self.tier)

    # --------------------------------------------------------------- scoping
    def may_see_all_clients(self) -> bool:
        """Owner, admin and head coach work across the whole roster."""
        return self.tier in (TIER_OWNER, 1, 2)

    def describe(self) -> dict:
        return {
            "id": self.id,
            "username": self.account.username,
            "tier": self.tier,
            "role": self.role,
            "is_owner": self.is_owner,
            "client_id": self.client_id,
            "coach_id": self.coach_id,
        }


def get_principal(
    db: DbSession,
    credentials: Credentials,
) -> Principal:
    """Resolve the bearer token to an active account."""
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR

    try:
        claims = security.decode_token(credentials.credentials, app="n6", expect_typ="access")
    except security.TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    account = db.get(Account, int(claims["sub"]))
    if account is None or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is missing or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(account, claims)


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]


# ------------------------------------------------------------------- the gate
def _denied(detail: str, principal: Principal) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "access_denied",
            "reason": detail,
            "tier": principal.tier,
            "role": principal.role,
        },
    )


def require(domain: str, action: str):
    """
    FastAPI dependency factory: refuse unless this tier may do `action` on
    `domain`.

        @router.post("/clients", dependencies=[Depends(require("clients", "create"))])

    The domain/action pair is exactly the key used in the ``actions`` block of
    backend/tiers/*.json, which is the same block js/core/access.js reads, so a
    control hidden in the UI and a route refused here agree by construction.
    """

    def _dependency(principal: CurrentPrincipal) -> Principal:
        if not can_perform(principal.tier, domain, action):
            raise _denied(f"'{action}' on '{domain}' needs a higher tier", principal)
        return principal

    _dependency.__name__ = f"require_{domain}_{action}"
    _dependency.__doc__ = f"Require {domain}.{action} for the caller's tier."
    return _dependency


def require_tier(maximum_tier: int):
    """
    FastAPI dependency factory: refuse anything above `maximum_tier`.

    `maximum_tier` is the least privileged tier allowed through, so
    ``require_tier(1)`` means admin and owner only. Use this when a whole
    screen is closed rather than one action on an open one, e.g. finance.
    """

    def _dependency(principal: CurrentPrincipal) -> Principal:
        if principal.tier > maximum_tier:
            raise _denied(f"needs tier <= {maximum_tier}", principal)
        return principal

    _dependency.__name__ = f"require_tier_{maximum_tier}"
    _dependency.__doc__ = f"Require a tier at or above {maximum_tier} (lower number = more access)."
    return _dependency


def require_owner(principal: CurrentPrincipal) -> Principal:
    """Tier 0 only: account administration and tier changes."""
    if not is_owner(principal.tier):
        raise _denied("owner only", principal)
    return principal


def require_menu(menu_key: str):
    """
    FastAPI dependency factory for menu-level gates, e.g. ``require_menu("komisi")``.

    Useful when an endpoint backs a whole sidebar entry rather than a single
    button. The menu keys match the ``data-panel`` attributes already on the
    navigation elements, so no parallel vocabulary is introduced.
    """

    def _dependency(principal: CurrentPrincipal) -> Principal:
        if not can_access_menu(principal.tier, menu_key):
            raise _denied(f"menu '{menu_key}' is not available at this tier", principal)
        return principal

    _dependency.__name__ = "require_menu_" + "".join(ch if ch.isalnum() else "_" for ch in menu_key)
    _dependency.__doc__ = f"Require access to the '{menu_key}' menu."
    return _dependency


# ------------------------------------------------------------------ month key
def period_query(
    period: str | None = Query(
        None,
        pattern=PERIOD_RE,
        description="YYYY-MM; omitted means the current month",
    ),
) -> str:
    """
    The `period` query parameter every month-scoped screen sends.

    A plain str rather than a Pydantic model on purpose: FastAPI would classify
    a BaseModel parameter as a request body, which on a GET is an empty body and
    a 422. So the pattern check and the "this month" default live here, once,
    instead of in seven routers.
    """
    return period or current_month()


#: `period: PeriodQuery` in a handler signature.
PeriodQuery = Annotated[str, Depends(period_query)]


def ensure_client_scope(db: Session, principal: Principal, client_id: int | None) -> None:
    """
    Reject reading somebody else's client record.

    Owner, admin and head coach may address anybody. A tier-4 client may only
    address its own row, and a coach only a client on their roster.
    """
    if principal.may_see_all_clients():
        return
    if client_id is None:
        raise _denied("a client id is required", principal)

    if principal.client_id is not None:
        if int(client_id) != int(principal.client_id):
            raise _denied("a client may only reach their own record", principal)
        return

    if principal.coach_id is not None:
        target = db.get(Client, int(client_id))
        if target is None or int(target.coach_id or 0) != int(principal.coach_id):
            raise _denied("a coach may only reach clients on their roster", principal)
        return

    raise _denied("this account is not linked to a client or a coach", principal)


def touch_last_login(db: Session, account: Account) -> None:
    account.last_login_at = datetime.now(timezone.utc)
    db.add(account)


def tier_summary(tier: int) -> dict:
    """Echo the server's own matrix, for /auth/me and /auth/tiers."""
    matrix = tier_matrix_for(tier)
    if matrix is None:
        return {"tier": tier, "role": role_for_tier(tier), "unrestricted": True}
    summary = matrix.summary()
    summary["unrestricted"] = False
    return summary