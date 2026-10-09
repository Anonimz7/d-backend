from __future__ import annotations
"""
/finance - menu: Keuangan (owner only).

Tier 1 admin has an empty `finance` action list in its tier file, so every
route here 403s for anyone but owner. The whole module is mounted anyway so the
OpenAPI document shows the surface, and so the reason for the refusal is the
tier rule rather than a 404 from a route that was never registered.

The sums come from core.metrics, which the monthly report and the client portal
also use, so the three cannot disagree about the same month.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/finance.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from .. import metrics
from ..period import month_bounds, series
from ..models import Expense
from ..schemas.common import CountByCategory, Ok, Page
from ..schemas.finance import (
    ExpenseCreate,
    ExpenseRead,
    FinanceMonthly,
    FinanceSummary,
)
from ..deps import CurrentPrincipal, DbSession, PeriodQuery, require

router = APIRouter(prefix="/finance", tags=["finance"])


def _summary(db, period: str) -> FinanceSummary:
    start, end = month_bounds(period)

    revenue = metrics.revenue(db, start, end)
    expenses = metrics.expenses(db, start, end)
    commission = metrics.commission(db, start, end)

    return FinanceSummary(
        period=period,
        revenue=float(revenue),
        expenses=float(expenses),
        commission=float(commission),
        profit=float(revenue - expenses - commission),
        new_clients=metrics.new_clients(db, start, end),
        active_clients=metrics.active_clients(db),
        revenue_by_category=[
            CountByCategory(key=category or "lainnya", label=category or "Lainnya",
                            count=0, amount=float(total))
            for category, total in metrics.revenue_by_category(db, start, end)
        ],
    )


@router.get("/summary", response_model=FinanceSummary, summary="Month headline figures",
            dependencies=[Depends(require("finance", "view"))])
def summary(period: PeriodQuery, db: DbSession) -> FinanceSummary:
    return _summary(db, period)


@router.get("/monthly", response_model=FinanceMonthly, summary="Trend across N months",
            dependencies=[Depends(require("finance", "view"))])
def monthly(
    period: PeriodQuery,
    db: DbSession,
    months: int = Query(12, ge=1, le=36, description="How many months back, inclusive"),
) -> FinanceMonthly:
    return FinanceMonthly(rows=[_summary(db, key) for key in series(period, months)])


@router.get("/expenses", response_model=Page[ExpenseRead], summary="List expenses",
            dependencies=[Depends(require("finance", "view"))])
def list_expenses(
    db: DbSession,
    period: PeriodQuery,
    category: str | None = Query(None, max_length=80),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[ExpenseRead]:
    start, end = month_bounds(period)
    filters = [Expense.spent_on >= start, Expense.spent_on <= end]
    if category:
        filters.append(Expense.category == category)

    total = int(db.scalar(select(func.count()).select_from(Expense).where(*filters)) or 0)
    rows = db.scalars(
        select(Expense)
        .where(*filters)
        .order_by(Expense.spent_on.desc(), Expense.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return Page[ExpenseRead](
        items=[ExpenseRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED,
             summary="Record an expense",
             dependencies=[Depends(require("finance", "view"))])
def create_expense(
    payload: ExpenseCreate, db: DbSession, principal: CurrentPrincipal
) -> ExpenseRead:
    """
    Guarded on finance.view, matching the tier file. If a deployment separates
    "read the books" from "write to the books", add a finance.manage action and
    change this and the tier JSON together - they are one rule in two places.
    """
    expense = Expense(
        category=payload.category.strip(),
        amount=payload.amount,
        spent_on=payload.spent_on,
        description=payload.description,
        created_by=principal.id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return ExpenseRead.model_validate(expense)


@router.delete("/expenses/{expense_id}", response_model=Ok, summary="Delete an expense",
               dependencies=[Depends(require("finance", "view"))])
def delete_expense(expense_id: int, db: DbSession) -> Ok:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    db.delete(expense)
    db.commit()
    return Ok(detail="Expense deleted")