from __future__ import annotations
"""
/accounts - user administration.

Reading the list is allowed to anyone who can open an account screen, but
creating, changing a tier or deactivating is owner-only: a lower tier must not
be able to hand itself more access, and that has to be enforced here rather
than in the browser.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/accounts.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core import security
from ..tiers import TIER_ADMIN, TIER_MAX, tier_matrix_for
from ..models import Account
from ..schemas.account import AccountCreate, AccountPatch, AccountRead, TierChange
from ..schemas.common import Ok, Page
from ..deps import CurrentPrincipal, DbSession, require, require_owner

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _get(db, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return account


@router.get("", response_model=Page[AccountRead], summary="List accounts",
            dependencies=[Depends(require("accounts", "view"))])
def list_accounts(
    db: DbSession,
    principal: CurrentPrincipal,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    tier: int | None = Query(None, ge=0, le=TIER_MAX),
    is_active: bool | None = None,
    q: str | None = Query(None, max_length=120),
) -> Page[AccountRead]:
    """Tier-filtered list. A non-owner sees no higher tier than their own."""
    stmt = select(Account)
    count_stmt = select(func.count()).select_from(Account)

    filters = []
    if tier is not None:
        filters.append(Account.tier == tier)
    if is_active is not None:
        filters.append(Account.is_active.is_(is_active))
    if q:
        like = f"%{q.strip().lower()}%"
        filters.append(
            or_(
                func.lower(Account.username).like(like),
                func.lower(Account.full_name).like(like),
            )
        )
    if not principal.is_owner:
        # Nobody below owner can see an account above their own tier.
        filters.append(Account.tier >= principal.tier)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(stmt.order_by(Account.tier, Account.full_name).limit(limit).offset(offset)).all()
    return Page[AccountRead](
        items=[AccountRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account (owner only)",
    dependencies=[Depends(require_owner)],
)
def create_account(payload: AccountCreate, db: DbSession) -> AccountRead:
    exists = db.scalar(select(Account).where(func.lower(Account.username) == payload.username.lower()))
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if payload.email:
        clash = db.scalar(select(Account).where(func.lower(Account.email) == payload.email.lower()))
        if clash is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

    account = Account(
        username=payload.username.strip(),
        full_name=payload.full_name.strip(),
        email=(payload.email or None),
        phone=payload.phone,
        password_hash=security.hash_password(payload.password),
        tier=payload.tier,
        client_id=payload.client_id,
        coach_id=payload.coach_id,
        is_active=payload.is_active,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return AccountRead.model_validate(account)


@router.patch("/{account_id}", response_model=AccountRead, summary="Edit an account (owner only)",
             dependencies=[Depends(require_owner)])
def update_account(account_id: int, payload: AccountPatch, db: DbSession) -> AccountRead:
    account = _get(db, account_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    account.updated_at = datetime.now(timezone.utc)
    db.add(account)
    db.commit()
    db.refresh(account)
    return AccountRead.model_validate(account)


@router.put(
    "/{account_id}/tier",
    response_model=AccountRead,
    summary="Change an account's tier (owner only)",
    dependencies=[Depends(require_owner)],
)
def set_tier(account_id: int, payload: TierChange, db: DbSession) -> AccountRead:
    """
    Move an account between tiers.

    Tier 0 is refused here on purpose: owner has no tier file, so an owner row
    created through this endpoint could not be described by the matrix and
    would silently become all-access. Bootstrapping the first owner is a
    separate, offline step.
    """
    account = _get(db, account_id)
    if account.tier < TIER_ADMIN and payload.tier != account.tier:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An owner account cannot be re-tiered through the API",
        )
    if tier_matrix_for(payload.tier) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No tier file describes tier {payload.tier}",
        )

    account.tier = payload.tier
    account.updated_at = datetime.now(timezone.utc)
    db.add(account)
    db.commit()
    db.refresh(account)
    return AccountRead.model_validate(account)


@router.delete("/{account_id}", response_model=Ok, summary="Deactivate an account (owner only)",
               dependencies=[Depends(require_owner)])
def deactivate_account(account_id: int, db: DbSession, principal: CurrentPrincipal) -> Ok:
    """
    Deactivate rather than delete.

    Tickets, messages and financial rows reference the account; a hard delete
    would either cascade away the audit trail or block on the foreign keys.
    """
    account = _get(db, account_id)
    if account.id == principal.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate yourself")
    account.is_active = False
    db.add(account)
    db.commit()
    return Ok(detail=f"{account.username} deactivated")