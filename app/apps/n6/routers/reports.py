from __future__ import annotations
"""
/reports - the monthly PDF/JSON report behind the Laporan menu.

`GET /reports/monthly` lists reports that have already been generated.
`POST /reports/monthly` computes one and, unless `dry_run`, freezes it into
`monthly_reports.payload`. Freezing is deliberate: the payload is stored as it
was at generation time, so re-running for a corrected month creates a new row
rather than rewriting a document somebody has already been handed.

The PDF itself is still assembled in the browser by the jspdf bundle that came
with the dashboards. This endpoint produces the figures; the download button
draws them. Splitting it that way keeps the report layout in the file that
already has it, instead of duplicating it in Python and letting the two drift.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/reports.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from .. import metrics
from ..period import month_bounds
from ..models import (
    AthleteNote,
    Attendance,
    Client,
    Coach,
    Enrollment,
    MonthlyReport,
    Program,
)
from ..schemas.common import CountByCategory, Page
from ..schemas.report import (
    ClientSummary,
    MonthlyReportCreate,
    MonthlyReportRead,
    ReportSummary,
)
from ..deps import CurrentPrincipal, DbSession, PeriodQuery, ensure_client_scope, require

router = APIRouter(prefix="/reports", tags=["reports"])

SCOPES = ("all", "coach", "client", "finance")


def _coach_performance(db, period: str) -> list[CountByCategory]:
    """
    Commission per coach for the month, largest first.

    Reads the same Enrollment rows `metrics.revenue` sums, but grouped by coach,
    so the "who brought in what" bar chart and the revenue total come from one
    table.
    """
    start, end = month_bounds(period)
    rows = db.execute(
        select(Coach.name, func.coalesce(func.sum(Enrollment.price_paid), 0))
        .join(Enrollment, Enrollment.coach_id == Coach.id, isouter=True)
        .where(Enrollment.start_on >= start, Enrollment.start_on <= end)
        .group_by(Coach.id, Coach.name)
        .order_by(func.coalesce(func.sum(Enrollment.price_paid), 0).desc())
    ).all()
    return [
        CountByCategory(key=str(index), label=name or "unassigned", count=0, amount=float(total))
        for index, (name, total) in enumerate(rows, start=1)
    ]


def build_report(db, period: str) -> ReportSummary:
    """
    The figures behind one month.

    Public because /portal/reports/summary returns the same thing to a client,
    and two copies of these sums is two chances for the Beranda card and the
    Laporan table to print different numbers for the same month.
    """
    start, end = month_bounds(period)
    revenue = metrics.revenue(db, start, end)
    expenses = metrics.expenses(db, start, end)
    commission = metrics.commission(db, start, end)

    return ReportSummary(
        period=period,
        revenue=float(revenue),
        commission=float(commission),
        expenses=float(expenses),
        profit=float(revenue - expenses - commission),
        new_clients=metrics.new_clients(db, start, end),
        active_clients=metrics.active_clients(db),
        new_clients_series=metrics.new_clients_weekly(db, start, end),
        revenue_by_category=[
            CountByCategory(key=category or "lainnya", label=category or "Lainnya",
                            count=0, amount=float(total))
            for category, total in metrics.revenue_by_category(db, start, end)
        ],
        coach_performance=_coach_performance(db, period),
        generated_at=datetime.now(timezone.utc),
    )


def _find(db, period: str, scope: str, audience: str) -> MonthlyReport | None:
    return db.scalar(
        select(MonthlyReport).where(
            MonthlyReport.period == period,
            MonthlyReport.scope == scope,
            MonthlyReport.audience == audience,
        )
    )


@router.get("/monthly", response_model=Page[MonthlyReportRead],
            summary="Reports already generated",
            dependencies=[Depends(require("reports", "view"))])
def list_reports(
    db: DbSession,
    period: PeriodQuery,
    scope: str | None = Query(None, pattern=r"^(all|coach|client|finance)$"),
    limit: int = Query(24, ge=1, le=120),
    offset: int = Query(0, ge=0),
) -> Page[MonthlyReportRead]:
    filters = [MonthlyReport.period == period]
    if scope:
        filters.append(MonthlyReport.scope == scope)

    total = int(
        db.scalar(select(func.count()).select_from(MonthlyReport).where(*filters)) or 0
    )
    rows = db.scalars(
        select(MonthlyReport)
        .where(*filters)
        .order_by(MonthlyReport.audience)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page[MonthlyReportRead](
        items=[MonthlyReportRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/monthly", response_model=MonthlyReportRead,
             status_code=status.HTTP_201_CREATED,
             summary="Generate a month-end report",
             dependencies=[Depends(require("reports", "generate"))])
def generate(
    payload: MonthlyReportCreate, db: DbSession, principal: CurrentPrincipal
) -> MonthlyReportRead:
    """
    Compute the figures and freeze them.

    Re-generating the same (period, scope, audience) overwrites the payload:
    that is the repair path for a month whose books were corrected, and it is
    only safe because the payload is a snapshot nobody has been handed unless
    they asked for it again.

    With `dry_run` nothing is written at all - the answer comes back with id 0,
    so a caller can tell "not stored" from "stored" without a second request.
    """
    if payload.scope not in SCOPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"scope must be one of {', '.join(SCOPES)}",
        )

    figures = build_report(db, payload.period)

    if payload.dry_run:
        transient = MonthlyReport(
            period=payload.period,
            scope=payload.scope,
            audience=payload.audience,
            generated_by=principal.id,
            payload=figures.model_dump(mode="json"),
        )
        return MonthlyReportRead.model_validate(transient)

    row = _find(db, payload.period, payload.scope, payload.audience)
    if row is not None and row.generated_by not in (None, principal.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another account generated this report; review before overwriting",
        )

    if row is None:
        row = MonthlyReport(
            period=payload.period, scope=payload.scope, audience=payload.audience
        )
    row.generated_by = principal.id
    row.payload = figures.model_dump(mode="json")
    db.add(row)
    db.commit()
    db.refresh(row)
    return MonthlyReportRead.model_validate(row)


@router.get("/preview", response_model=ReportSummary,
            summary="Figures for a month, computed but not stored",
            dependencies=[Depends(require("reports", "view"))])
def preview(period: PeriodQuery, db: DbSession) -> ReportSummary:
    """
    The same numbers `POST /reports/monthly` would freeze, returned without
    being stored.

    This is what the Report page loads on open, so opening the screen never
    creates a row - only pressing Generate does.
    """
    return build_report(db, period)


@router.get("/clients/{client_id}/summary", response_model=ClientSummary,
            summary="The client portal card",
            dependencies=[Depends(require("reports", "view"))])
def client_summary(
    client_id: int, db: DbSession, principal: CurrentPrincipal, period: PeriodQuery
) -> ClientSummary:
    """
    One client's month: attendance, current programme, latest measurement.

    Scoped through `ensure_client_scope`, so a client asking for their own card
    and a head coach asking for anyone's resolve to the same code path.
    """
    ensure_client_scope(db, principal, client_id)
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    start, end = month_bounds(period)
    counts = db.execute(
        select(Attendance.status, func.count()).where(
            Attendance.client_id == client_id,
            Attendance.session_on >= start,
            Attendance.session_on <= end,
        )
        .group_by(Attendance.status)
    ).all()

    # izin and sakit count as attended: the session happened, the client was
    # not at fault. Only 'alpha' is a miss.
    attended = sum(count for presence, count in counts if presence != "alpha")
    sessions = sum(count for _, count in counts)

    enrollment = db.scalar(
        select(Enrollment)
        .where(Enrollment.client_id == client_id, Enrollment.start_on <= end)
        .order_by(Enrollment.start_on.desc())
    )
    program_name = None
    program_ends_on = None
    if enrollment is not None:
        program = db.get(Program, enrollment.program_id)
        program_name = enrollment.custom_label or (
            program.name if program is not None else None
        )
        program_ends_on = enrollment.end_on

    latest = db.scalar(
        select(AthleteNote)
        .where(AthleteNote.client_id == client_id, AthleteNote.period.is_not(None))
        .order_by(AthleteNote.period.desc())
    )
    latest_measurement = None
    if latest is not None and (latest.pace_target or latest.hr_target):
        latest_measurement = ", ".join(
            part
            for part in (
                latest.pace_target,
                f"{latest.hr_target} bpm" if latest.hr_target else None,
            )
            if part
        )

    return ClientSummary(
        client_id=client.id,
        client_name=client.name,
        period=period,
        attendance_rate=round(attended / sessions, 4) if sessions else 0.0,
        sessions_attended=attended,
        sessions_scheduled=sessions,
        program_name=program_name,
        program_ends_on=program_ends_on,
        latest_measurement=latest_measurement,
        measurement_period=latest.period if latest is not None else None,
    )