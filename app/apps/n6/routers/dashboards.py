from __future__ import annotations
"""
/dashboards - read-only aggregates for the coach screens.

Nothing here writes. Every number is derived from the tables the existing
menus already maintain (clients, attendance, schedules, commissions,
athlete_notes, schedule_requests), so the dashboard can never disagree with
the source screens. Tier 3's commission figure is computed, not entered,
same as GET /commissions/summary.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from .commissions import _recompute as _recompute_commission
from ..deps import (
    CurrentPrincipal,
    DbSession,
    ensure_client_scope,
    require,
)
from ..models import (
    CLIENT_ACTIVE,
    AthleteNote,
    Attendance,
    Client,
    Coach,
    CoachScheduleSlot,
    Commission,
    ScheduleRequest,
)
from ..period import current_month
from ..schemas.dashboard import (
    ActivityItem,
    AttendanceTrend,
    ClientCount,
    ClientProgress,
    ClientProgressItem,
    ClientProgressSessions,
    ClientReport,
    CoachDashboard,
    CommissionInfo,
    HeadcoachDashboard,
    SessionHistoryItem,
    TeamCoachItem,
    TodaySlot,
)

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

# ------------------------------------------------------------------ helpers
def _resolve_coach(principal: CurrentPrincipal, coach_id: int | None) -> int:
    """Tier 3 sees only their own coach row; staff may name one explicitly."""
    if principal.coach_id is not None:
        return int(principal.coach_id)
    if coach_id is not None:
        return int(coach_id)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="A coach id is required for this account",
    )


def _attendance_stats(db, client_id: int) -> tuple[int, int]:
    """(hadir, total) sessions for one client, all time."""
    rows = db.execute(
        select(Attendance.status, func.count())
        .where(Attendance.client_id == client_id)
        .group_by(Attendance.status)
    ).all()
    hadir = sum(count for st, count in rows if st == "hadir")
    total = sum(count for _, count in rows)
    return hadir, total


def _pct(hadir: int, total: int) -> float:
    return round(hadir / total * 100, 1) if total else 0.0


def _client_name(db, client_id: int) -> str | None:
    row = db.get(Client, client_id)
    return row.name if row else None


def _coach_name(db, coach_id: int) -> str | None:
    row = db.get(Coach, coach_id)
    return row.name if row else None


# ------------------------------------------------------------ GET coach/me
@router.get("/coach/me", response_model=CoachDashboard,
            summary="Coach dashboard: roster, progress, today, commission",
            dependencies=[Depends(require("clients", "view"))])
def coach_dashboard(
    db: DbSession,
    principal: CurrentPrincipal,
    coach_id: int | None = Query(
        None, description="Staff only: read another coach's dashboard"),
) -> CoachDashboard:
    cid = _resolve_coach(principal, coach_id)
    coach = db.get(Coach, cid)
    if coach is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")

    roster = db.scalars(
        select(Client).where(Client.coach_id == cid).order_by(Client.name)
    ).all()

    by_status: dict[str, int] = {}
    for c in roster:
        by_status[c.status] = by_status.get(c.status, 0) + 1

    progress: list[ClientProgressItem] = []
    for c in roster:
        hadir, total = _attendance_stats(db, c.id)
        last = db.scalar(
            select(Attendance)
            .where(Attendance.client_id == c.id)
            .order_by(Attendance.session_on.desc())
            .limit(1)
        )
        progress.append(ClientProgressItem(
            client_id=c.id,
            name=c.name,
            pct=_pct(hadir, total),
            sessions=total,
            hadir=hadir,
            last_session=last.session_on if last else None,
            note=last.note if last else None,
        ))

    weekday = date.today().isoweekday()  # 1 = Monday .. 7 = Sunday
    slots = db.scalars(
        select(CoachScheduleSlot)
        .where(
            CoachScheduleSlot.coach_id == cid,
            CoachScheduleSlot.weekday == weekday,
            CoachScheduleSlot.active.is_(True),
        )
        .order_by(CoachScheduleSlot.start_time)
    ).all()
    today_schedule = [
        TodaySlot(
            start_time=s.start_time,
            end_time=s.end_time,
            location=s.location,
            training_category=s.training_category,
            note=s.note,
        )
        for s in slots
    ]

    period = current_month()
    row = _recompute_commission(db, coach, period)
    commission = CommissionInfo(
        period=period,
        gross=float(row.gross or 0),
        amount=float(row.amount or 0),
        paid=bool(row.paid),
        rate=float(row.rate or 0),
    )

    return CoachDashboard(
        coach_id=cid,
        coach_name=coach.name,
        clients=ClientCount(
            total=len(roster),
            aktif=sum(1 for c in roster if c.status == CLIENT_ACTIVE),
            by_status=by_status,
        ),
        progress=progress,
        today_schedule=today_schedule,
        commission=commission,
    )


# ------------------------------------------------------ GET headcoach/team
@router.get("/headcoach/team", response_model=HeadcoachDashboard,
            summary="Head coach dashboard: team, trends, activity",
            dependencies=[Depends(require("monitoring", "view"))])
def headcoach_dashboard(db: DbSession) -> HeadcoachDashboard:
    coaches = db.scalars(select(Coach).order_by(Coach.name)).all()

    team: list[TeamCoachItem] = []
    for coach in coaches:
        client_ids = db.scalars(
            select(Client.id).where(Client.coach_id == coach.id)
        ).all()
        rows = db.execute(
            select(Attendance.status, func.count())
            .where(Attendance.coach_id == coach.id)
            .group_by(Attendance.status)
        ).all()
        hadir = sum(count for st, count in rows if st == "hadir")
        total = sum(count for _, count in rows)
        team.append(TeamCoachItem(
            coach_id=coach.id,
            name=coach.name,
            client_count=len(client_ids),
            attendance_pct=_pct(hadir, total),
            rating=None,  # no rating source yet
        ))

    client_status: dict[str, int] = {}
    for st, count in db.execute(
        select(Client.status, func.count()).group_by(Client.status)
    ).all():
        client_status[st] = count

    # Four Monday..Sunday weeks ending this week, oldest first.
    today = date.today()
    monday = today - timedelta(days=today.isoweekday() - 1)
    labels: list[str] = []
    values: list[float] = []
    for back in range(3, -1, -1):
        start = monday - timedelta(weeks=back)
        end = start + timedelta(days=6)
        rows = db.execute(
            select(Attendance.status, func.count())
            .where(Attendance.session_on >= start, Attendance.session_on <= end)
            .group_by(Attendance.status)
        ).all()
        hadir = sum(count for st, count in rows if st == "hadir")
        total = sum(count for _, count in rows)
        labels.append(start.strftime("%d/%m"))
        values.append(_pct(hadir, total))

    activities: list[ActivityItem] = []

    recent_att = db.scalars(
        select(Attendance).order_by(Attendance.session_on.desc()).limit(8)
    ).all()
    for a in recent_att:
        activities.append(ActivityItem(
            type="attendance",
            label=f"{a.status} - {a.session_on.strftime('%d/%m')}",
            at=datetime.combine(a.session_on, datetime.min.time()),
            client_id=a.client_id,
            client_name=_client_name(db, a.client_id),
            coach_name=_coach_name(db, a.coach_id) if a.coach_id else None,
        ))

    recent_req = db.scalars(
        select(ScheduleRequest).order_by(ScheduleRequest.requested_on.desc()).limit(4)
    ).all()
    for r in recent_req:
        activities.append(ActivityItem(
            type="schedule_request",
            label=f"pengajuan reschedule: {r.status}",
            at=datetime.combine(r.requested_on, datetime.min.time()),
            client_id=r.client_id,
            client_name=_client_name(db, r.client_id),
            coach_name=_coach_name(db, r.coach_id) if r.coach_id else None,
        ))

    recent_flags = db.scalars(
        select(AthleteNote).order_by(AthleteNote.updated_at.desc()).limit(4)
    ).all()
    for n in recent_flags:
        flagged = [f for f in (n.flag_kehadiran, n.flag_ordinal, n.flag_komisi) if f]
        if not flagged:
            continue
        activities.append(ActivityItem(
            type="monitoring_flag",
            label=f"flag: {', '.join(flagged)}",
            at=n.updated_at,
            client_id=n.client_id,
            client_name=_client_name(db, n.client_id),
        ))

    activities.sort(key=lambda a: a.at or datetime.min, reverse=True)
    activities = activities[:8]

    return HeadcoachDashboard(
        coaches=team,
        client_status=client_status,
        attendance_trend=AttendanceTrend(labels=labels, values=values),
        activities=activities,
    )


# -------------------------------------------- GET clients/{id}/progress
@router.get("/clients/{client_id}/progress", response_model=ClientProgress,
            summary="One client's sessions, report card and history",
            dependencies=[Depends(require("clients", "view"))])
def client_progress(
    client_id: int,
    db: DbSession,
    principal: CurrentPrincipal,
) -> ClientProgress:
    ensure_client_scope(db, principal, client_id)
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    hadir, total = _attendance_stats(db, client_id)

    note = db.scalar(
        select(AthleteNote)
        .where(AthleteNote.client_id == client_id)
        .order_by(AthleteNote.period.desc().nullslast())
        .limit(1)
    )
    report = ClientReport(
        pace_target=note.pace_target if note else None,
        intensity=note.intensity if note else None,
        note=note.note if note else None,
        distance_total=None,  # no distance source yet
    )

    rows = db.scalars(
        select(Attendance)
        .where(Attendance.client_id == client_id)
        .order_by(Attendance.session_on.desc())
        .limit(10)
    ).all()
    history = [
        SessionHistoryItem(session_on=r.session_on, status=r.status, note=r.note)
        for r in rows
    ]

    return ClientProgress(
        client_id=client.id,
        name=client.name,
        sessions=ClientProgressSessions(
            total=total, hadir=hadir, pct=_pct(hadir, total)),
        report=report,
        history=history,
    )
