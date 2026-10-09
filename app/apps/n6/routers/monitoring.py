from __future__ import annotations
"""
/monitoring - the head coach's roster view (menu Koreksi / Atlet Binaan).

The screen shows, in one row per client: that month's attendance rate, the
targets the head coach set, and the three tri-state flags. Rather than one
eleven-column join with colliding `id` labels, this reads clients, then their
notes, then one grouped attendance count, and assembles the row in Python.
Three round trips, and the row is always internally consistent because it is
built in one place.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/monitoring.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from ..period import month_bounds
from ..models import CLIENT_ACTIVE, AthleteNote, Attendance, Client, Coach, Commission
from ..schemas.common import Page
from ..schemas.support import AthleteRead
from ..deps import CurrentPrincipal, DbSession, PeriodQuery, require

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _attendance_map(db, principal: CurrentPrincipal, period: str) -> dict[int, tuple[int, int]]:
    """{client_id: (present, sessions)} for the month. One grouped query."""
    start, end = month_bounds(period)
    stmt = select(Attendance.client_id, Attendance.status, func.count()).where(
        Attendance.session_on >= start, Attendance.session_on <= end
    )
    if not principal.may_see_all_clients() and principal.coach_id is not None:
        stmt = stmt.where(Attendance.coach_id == principal.coach_id)

    counts: dict[int, tuple[int, int]] = {}
    for client_id, presence, count in db.execute(
        stmt.group_by(Attendance.client_id, Attendance.status)
    ).all():
        present, sessions = counts.get(client_id, (0, 0))
        counts[client_id] = (present + (count if presence == "hadir" else 0), sessions + count)
    return counts


@router.get("/clients", response_model=Page[AthleteRead],
            summary="Roster rows: attendance, targets, flags",
            dependencies=[Depends(require("monitoring", "view"))])
def roster(
    db: DbSession,
    principal: CurrentPrincipal,
    period: PeriodQuery,
    q: str | None = Query(None, max_length=120),
    coach_id: int | None = None,
    flagged_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[AthleteRead]:
    filters = [Client.status == CLIENT_ACTIVE]
    if q:
        term = q.strip()
        filters.append(
            or_(
                Client.name.ilike(f"%{term}%"),
                func.coalesce(Client.phone, "").ilike(f"%{term}%"),
            )
        )
    if coach_id is not None:
        filters.append(Client.coach_id == coach_id)
    if not principal.may_see_all_clients() and principal.coach_id is not None:
        filters.append(Client.coach_id == principal.coach_id)

    total = int(db.scalar(select(func.count()).select_from(Client).where(*filters)) or 0)
    clients = db.scalars(
        select(Client).where(*filters).order_by(Client.name).limit(limit).offset(offset)
    ).all()

    ids = [c.id for c in clients] or [-1]
    notes = {
        note.client_id: note
        for note in db.scalars(
            select(AthleteNote).where(
                AthleteNote.client_id.in_(ids),
                AthleteNote.period == period,
            )
        ).all()
    }
    counts = _attendance_map(db, principal, period)

    items: list[AthleteRead] = []
    for client in clients:
        note = notes.get(client.id)
        if flagged_only and (note is None or not (note.flag_kehadiran or note.flag_komisi)):
            continue
        present, sessions = counts.get(client.id, (0, 0))
        items.append(
            AthleteRead(
                id=note.id if note is not None else 0,
                client_id=client.id,
                client_name=client.name,
                period=period,
                pace_target=note.pace_target if note is not None else None,
                hr_target=note.hr_target if note is not None else None,
                intensity=note.intensity if note is not None else None,
                note=note.note if note is not None else None,
                flag_kehadiran=note.flag_kehadiran if note is not None else None,
                flag_ordinal=note.flag_ordinal if note is not None else None,
                flag_komisi=note.flag_komisi if note is not None else None,
                present=present,
                sessions=sessions,
                rate=round(present / sessions, 4) if sessions else 0.0,
            )
        )

    return Page[AthleteRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/summary", response_model=dict,
            summary="Attendance headline numbers for the month",
            dependencies=[Depends(require("monitoring", "view"))])
def summary(db: DbSession, principal: CurrentPrincipal, period: PeriodQuery) -> dict:
    """
    The numbers above the roster. Same grouped walk as `_attendance_map`, summed
    once, so the header and the rows cannot disagree.
    """
    counts = _attendance_map(db, principal, period)
    present = sum(c[0] for c in counts.values())
    sessions = sum(c[1] for c in counts.values())
    return {
        "period": period,
        "clients": len(counts),
        "present": present,
        "sessions": sessions,
        "rate": round(present / sessions, 4) if sessions else 0.0,
    }


@router.get("/flags", response_model=list[dict],
            summary="Only the rows that carry a flag",
            dependencies=[Depends(require("monitoring", "view"))])
def flags(period: PeriodQuery, db: DbSession) -> list[dict]:
    """
    Flagged clients only.

    The screen shows a fixed shortlist - attendance below 80%, a missing
    measurement, an unpaid month - so returning every athlete would push that
    filtering onto the caller, which is what this endpoint exists to avoid.
    """
    rows = db.execute(
        select(AthleteNote, Client)
        .join(Client, Client.id == AthleteNote.client_id)
        .where(
            AthleteNote.period == period,
            or_(
                AthleteNote.flag_kehadiran.is_not(None),
                AthleteNote.flag_komisi.is_not(None),
            ),
        )
        .order_by(Client.name)
    ).all()
    return [
        {
            "client_id": note.client_id,
            "client_name": client.name,
            "flag_kehadiran": note.flag_kehadiran,
            "flag_ordinal": note.flag_ordinal,
            "flag_komisi": note.flag_komisi,
            "note": note.note,
        }
        for note, client in rows
    ]


@router.get("/commission-check", response_model=list[dict],
            summary="Coaches whose commission is unsettled for the month",
            dependencies=[Depends(require("monitoring", "view"))])
def commission_check(period: PeriodQuery, db: DbSession) -> list[dict]:
    """
    Unpaid commission rows, largest first.

    A question the commission ledger cannot answer on its own: monitoring asks
    "is anything outstanding", the ledger asks "how much and who". Empty in the
    common case, which is why the caller treats the empty list as "all good"
    rather than as an error.
    """
    rows = db.execute(
        select(Commission, Coach)
        .join(Coach, Coach.id == Commission.coach_id)
        .where(Commission.period == period, Commission.paid.is_(False))
        .order_by(Commission.amount.desc())
    ).all()
    return [
        {
            "coach_id": commission.coach_id,
            "coach_name": coach.name,
            "period": commission.period,
            "rate": float(commission.rate),
            "gross": float(commission.gross),
            "amount": float(commission.amount),
        }
        for commission, coach in rows
    ]