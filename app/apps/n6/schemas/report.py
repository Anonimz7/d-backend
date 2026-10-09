from __future__ import annotations
"""Monthly reports and the client-facing summary."""


from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .common import CountByCategory, ORMModel


class MonthlyReportRead(ORMModel):
    id: int
    period: str
    scope: str
    audience: str
    generated_by: int | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime | None = None


class MonthlyReportCreate(BaseModel):
    """POST /reports/monthly - generate now."""

    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    scope: str = Field(default="all", pattern=r"^(all|coach|client|finance)$")
    audience: str = Field(default="owner", max_length=32)
    #: Compute and return the figures without writing a row. The response
    #: carries id 0, so "not stored" is visible in the answer itself.
    dry_run: bool = False


class ReportSummary(BaseModel):
    """
    Figures behind one month, shaped like the Beranda analytics grid so the
    dashboard can draw the same cards from API data as from localStorage.

    ``new_clients_series`` is one bucket per 7-day block of the month, oldest
    first: a sign-up sparkline, not a multi-month series.
    """

    period: str
    revenue: float = 0.0
    commission: float = 0.0
    expenses: float = 0.0
    profit: float = 0.0
    new_clients: int = 0
    active_clients: int = 0
    new_clients_series: list[int] = Field(default_factory=list)
    revenue_by_category: list[CountByCategory] = Field(default_factory=list)
    coach_performance: list[CountByCategory] = Field(default_factory=list)
    generated_at: datetime | None = None


class ClientSummary(BaseModel):
    """GET /reports/clients/{client_id}/summary - the client portal card."""

    client_id: int
    client_name: str
    period: str
    attendance_rate: float = 0.0
    sessions_attended: int = 0
    sessions_scheduled: int = 0
    program_name: str | None = None
    program_ends_on: date | None = None
    #: The head coach's targets for the most recent month that has a note.
    latest_measurement: str | None = None
    measurement_period: str | None = None