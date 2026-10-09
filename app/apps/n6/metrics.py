from __future__ import annotations
"""
Money and roster figures, defined once.

The Keuangan screen (finance.py), the monthly report (reports.py) and the
client portal card all answer variants of the same three questions: how much
came in, how much went out, how many clients were around. Three copies of those
sums is three chances for the dashboard to print two different profits in the
same month, which is the exact failure this module exists to prevent.

Every function takes a plain Session and a ``YYYY-MM`` string, so callers need
no ORM objects and no period objects.
"""


from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    CLIENT_ACTIVE,
    Client,
    Commission,
    Enrollment,
    Expense,
    Program,
)
from .period import month_bounds


def revenue(db: Session, start: date, end: date) -> Decimal:
    """Money in: enrolments that started inside the window."""
    stmt = select(func.coalesce(func.sum(Enrollment.price_paid), 0)).where(
        Enrollment.start_on >= start, Enrollment.start_on <= end
    )
    return Decimal(db.scalar(stmt) or 0)


def expenses(db: Session, start: date, end: date) -> Decimal:
    stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.spent_on >= start, Expense.spent_on <= end
    )
    return Decimal(db.scalar(stmt) or 0)


def commission(db: Session, start: date, end: date) -> Decimal:
    """
    Summed from the Commission ledger rather than recomputed from enrolments.

    The ledger is what was settled, so the profit line on the Keuangan screen
    cannot quietly disagree with the figure on the Performa screen.
    """
    stmt = select(func.coalesce(func.sum(Commission.amount), 0)).where(
        Commission.period >= f"{start:%Y-%m}", Commission.period <= f"{end:%Y-%m}"
    )
    return Decimal(db.scalar(stmt) or 0)


def new_clients(db: Session, start: date, end: date) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Client)
            .where(Client.joined_on >= start, Client.joined_on <= end)
        )
        or 0
    )


def active_clients(db: Session) -> int:
    """Right now, not as of the period - the roster is a live thing."""
    return int(
        db.scalar(
            select(func.count()).select_from(Client).where(Client.status == CLIENT_ACTIVE)
        )
        or 0
    )


def new_clients_weekly(db: Session, start: date, end: date) -> list[int]:
    """
    New clients per week of the month, oldest first.

    Bucketed in Python rather than with date_trunc so the cut points are the
    same 7-day blocks on PostgreSQL and on SQLite, which keeps a local run and
    a deployed run comparable.
    """
    joined = db.scalars(
        select(Client.joined_on).where(Client.joined_on >= start, Client.joined_on <= end)
    ).all()

    weeks: list[int] = []
    bucket_start = start
    while bucket_start <= end:
        bucket_end = min(bucket_start + timedelta(days=6), end)
        weeks.append(sum(1 for d in joined if bucket_start <= d <= bucket_end))
        bucket_start = bucket_end + timedelta(days=1)
    return weeks


def revenue_by_category(db: Session, start: date, end: date) -> list[tuple[str, Decimal]]:
    """[(category, total)] for the month, unsorted - the caller orders it."""
    rows = db.execute(
        select(Program.category, func.coalesce(func.sum(Enrollment.price_paid), 0))
        .join(Enrollment, Enrollment.program_id == Program.id, isouter=True)
        .where(Enrollment.start_on >= start, Enrollment.start_on <= end)
        .group_by(Program.category)
    ).all()
    return [(category or "", Decimal(total or 0)) for category, total in rows]


def window(period: str) -> tuple[date, date]:
    """Re-exported so a caller needs one import for 'the month I am asking about'."""
    return month_bounds(period)