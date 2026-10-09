from __future__ import annotations
"""
Month arithmetic, shared by every endpoint that speaks ``YYYY-MM``.

Finance, commissions, attendance, monitoring, athletes, corrections and reports
all filter on the same string column. Keeping the parsing, the month-end day
count and the trend series in one module is what stops two screens disagreeing
about which days "March" covers - the sort of bug that is invisible until a
February report is short by three days.

Lives in core rather than in api/v1/endpoints so that app.api.deps can use it
without importing the routers that import deps.
"""


import calendar
from datetime import date

#: Same pattern the tier JSON and the frontend use.
PERIOD_RE = r"^\d{4}-\d{2}$"


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def parse(period: str) -> tuple[int, int]:
    """``'2026-03'`` -> ``(2026, 3)``. Raises ValueError on anything else."""
    year, month = (int(part) for part in period.split("-"))
    if not 1 <= month <= 12:
        raise ValueError(f"{period!r} is not a month")
    return year, month


def month_bounds(period: str) -> tuple[date, date]:
    """``'2026-03'`` -> ``(2026-03-01, 2026-03-31)``, inclusive on both ends."""
    year, month = parse(period)
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def shift(period: str, months: int) -> str:
    """Move `months` from `period`; negative goes back. Handles year rollover."""
    year, month = parse(period)
    index = year * 12 + (month - 1) + int(months)
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def series(period: str, count: int) -> list[str]:
    """
    `count` month keys ending at `period`, oldest first.

    Oldest first because the caller feeds it straight into a chart, where a
    reversed axis is a bug nobody notices until the screenshot.
    """
    return [shift(period, -offset) for offset in range(count - 1, -1, -1)]