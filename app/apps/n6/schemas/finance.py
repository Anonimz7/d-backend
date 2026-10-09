from __future__ import annotations
"""Money: expenses, commissions, payouts (menus: Keuangan, Performa & Komisi)."""


from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from .common import CountByCategory, ORMModel


class ExpenseCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(ge=0)
    spent_on: date = Field(default_factory=date.today)
    description: str | None = None


class ExpenseRead(ORMModel):
    id: int
    category: str
    amount: Decimal
    spent_on: date
    description: str | None = None
    created_at: datetime | None = None


class CommissionPatch(BaseModel):
    """PUT /commissions/{coach_id}"""

    rate: Decimal = Field(ge=0, le=1)
    period: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class PayoutRequest(BaseModel):
    """POST /commissions/{coach_id}/payout"""

    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    paid_on: date = Field(default_factory=date.today)
    note: str | None = Field(default=None, max_length=500)


class CommissionRead(ORMModel):
    id: int
    coach_id: int
    period: str
    rate: Decimal
    gross: Decimal
    amount: Decimal
    paid: bool
    paid_on: date | None = None


class CommissionSummary(BaseModel):
    """GET /commissions/summary"""

    period: str
    total_gross: float = 0.0
    total_commission: float = 0.0
    total_paid: float = 0.0
    outstanding: float = 0.0
    rows: list[CommissionRead] = Field(default_factory=list)
    by_coach: list[CountByCategory] = Field(default_factory=list)


class FinanceSummary(BaseModel):
    """GET /finance/summary - the Keuangan headline figures."""

    period: str
    revenue: float = 0.0
    expenses: float = 0.0
    commission: float = 0.0
    profit: float = 0.0
    new_clients: int = 0
    active_clients: int = 0
    revenue_by_category: list[CountByCategory] = Field(default_factory=list)


class FinanceMonthly(BaseModel):
    """GET /finance/monthly - one point per month for the trend chart."""

    rows: list[FinanceSummary] = Field(default_factory=list)