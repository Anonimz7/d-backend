from __future__ import annotations
"""
/commissions - menu: Performa & Komisi (owner only).

The tier files leave `commissions` empty for every tier below owner, so these
routes exist and answer 403 rather than 404. That keeps the reason in the
access rule instead of in the routing table.

A commission row is derived, not entered: gross comes from the month's paid
enrolments and amount from the coach's rate, so recalculating rebuilds the row
from the books and the number on the Performa screen can never drift from them.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/commissions.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from ..period import current_month, month_bounds
from ..models import PAYMENT_PAID, Coach, Commission, Enrollment
from ..schemas.common import CountByCategory, Ok
from ..schemas.finance import (
    CommissionPatch,
    CommissionRead,
    CommissionSummary,
    PayoutRequest,
)
from ..deps import DbSession, PeriodQuery, require

router = APIRouter(prefix="/commissions", tags=["commissions"])


def _get_coach(db, coach_id: int) -> Coach:
    coach = db.get(Coach, coach_id)
    if coach is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
    return coach


def _gross_for(db, coach_id: int, period: str) -> Decimal:
    """What this coach's paid enrolments were worth that month."""
    start, end = month_bounds(period)
    stmt = select(func.coalesce(func.sum(Enrollment.price_paid), 0)).where(
        Enrollment.coach_id == coach_id,
        Enrollment.start_on >= start,
        Enrollment.start_on <= end,
        Enrollment.payment_status == PAYMENT_PAID,
    )
    return Decimal(db.scalar(stmt) or 0)


def _row_for(db, coach: Coach, period: str) -> Commission:
    """Fetch or create this coach's row for the month, without saving."""
    row = db.scalar(
        select(Commission).where(
            Commission.coach_id == coach.id, Commission.period == period
        )
    )
    if row is None:
        row = Commission(
            coach_id=coach.id,
            period=period,
            rate=coach.commission_rate,
            gross=Decimal(0),
            amount=Decimal(0),
        )
    return row


def _recompute(db, coach: Coach, period: str, rate: Decimal | None = None) -> Commission:
    row = _row_for(db, coach, period)
    row.rate = coach.commission_rate if rate is None else rate
    row.gross = _gross_for(db, coach.id, period)
    row.amount = (row.gross * row.rate).quantize(Decimal("0.01"))
    db.add(row)
    return row


def _summary(db, period: str) -> CommissionSummary:
    rows = db.scalars(
        select(Commission).where(Commission.period == period).order_by(Commission.coach_id)
    ).all()

    total_gross = sum((r.gross for r in rows), Decimal(0))
    total_amount = sum((r.amount for r in rows), Decimal(0))
    total_paid = sum((r.amount for r in rows if r.paid), Decimal(0))

    by_coach = [
        CountByCategory(
            key=str(row.coach_id),
            label=_coach_name(db, row.coach_id),
            count=1,
            amount=float(row.amount),
        )
        for row in rows
    ]

    return CommissionSummary(
        period=period,
        total_gross=float(total_gross),
        total_commission=float(total_amount),
        total_paid=float(total_paid),
        outstanding=float(total_amount - total_paid),
        rows=[CommissionRead.model_validate(r) for r in rows],
        by_coach=by_coach,
    )


def _coach_name(db, coach_id: int) -> str:
    coach = db.get(Coach, coach_id)
    return coach.name if coach is not None else f"coach {coach_id}"


@router.get("/summary", response_model=CommissionSummary, summary="Commissions for one month",
            dependencies=[Depends(require("commissions", "view"))])
def summary(period: PeriodQuery, db: DbSession) -> CommissionSummary:
    return _summary(db, period)


@router.put("/{coach_id}", response_model=CommissionRead, summary="Set a coach's rate",
            dependencies=[Depends(require("commissions", "view"))])
def set_rate(coach_id: int, payload: CommissionPatch, db: DbSession) -> CommissionRead:
    """
    Change the standing rate, then rebuild the named month's row under it.

    Both halves in one call on purpose: saving a rate and leaving last month's
    figures on the old one is how a commission sheet stops matching the books.
    """
    coach = _get_coach(db, coach_id)
    coach.commission_rate = payload.rate
    db.add(coach)

    row = _recompute(db, coach, payload.period or current_month(), rate=payload.rate)
    db.commit()
    db.refresh(row)
    return CommissionRead.model_validate(row)


@router.post("/{coach_id}/recalculate", response_model=CommissionRead,
             summary="Recompute one coach's month from the books",
             dependencies=[Depends(require("commissions", "view"))])
def recalculate(coach_id: int, db: DbSession, period: PeriodQuery) -> CommissionRead:
    """Idempotent: safe to re-run after a late payment without double counting."""
    coach = _get_coach(db, coach_id)
    row = _recompute(db, coach, period)
    db.commit()
    db.refresh(row)
    return CommissionRead.model_validate(row)


@router.post("/{coach_id}/payout", response_model=CommissionRead,
             summary="Mark a month as paid out",
             dependencies=[Depends(require("commissions", "view"))])
def payout(coach_id: int, payload: PayoutRequest, db: DbSession) -> CommissionRead:
    row = db.scalar(
        select(Commission).where(
            Commission.coach_id == coach_id, Commission.period == payload.period
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No commission row for that coach and month; recalculate first",
        )
    if row.paid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already paid on {row.paid_on}",
        )
    row.paid = True
    row.paid_on = payload.paid_on
    db.add(row)
    db.commit()
    db.refresh(row)
    return CommissionRead.model_validate(row)


@router.delete("/{coach_id}/{period}", response_model=Ok, summary="Drop a commission row",
               dependencies=[Depends(require("commissions", "view"))])
def drop(coach_id: int, period: str, db: DbSession) -> Ok:
    """
    For clearing a recalculation mistake. A settled row is refused rather than
    deleted: the payout is a fact that happened, and deleting the row would
    quietly un-pay it.
    """
    row = db.scalar(
        select(Commission).where(
            Commission.coach_id == coach_id, Commission.period == period
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commission row not found"
        )
    if row.paid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A paid commission cannot be deleted; adjust the rate and recalculate",
        )
    db.delete(row)
    db.commit()
    return Ok(detail=f"Commission for {period} removed")