from __future__ import annotations
"""
/attendance - the absensi grid shared by the coach and head coach views.

One row per client per day is enforced by a unique constraint on
(client_id, session_on) as well as by the code: the grid saves a whole day's
worth of cells in one click, and a retry of that click must not double-count.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/attendance.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from ..period import month_bounds
from ..models import Attendance, Client
from ..schemas.common import Ok, Page
from ..schemas.support import AttendanceCreate, AttendanceRead
from ..deps import CurrentPrincipal, DbSession, PeriodQuery, ensure_client_scope, require

router = APIRouter(prefix="/attendance", tags=["attendance"])

VALID_STATUS = ("hadir", "izin", "sakit", "alpha")


def _scope(principal: CurrentPrincipal) -> list:
    """Rows a caller may see. Staff see everything; a client or coach sees theirs."""
    if principal.may_see_all_clients():
        return []
    if principal.client_id is not None:
        return [Attendance.client_id == principal.client_id]
    if principal.coach_id is not None:
        return [Attendance.coach_id == principal.coach_id]
    return [Attendance.client_id == -1]


@router.get("", response_model=Page[AttendanceRead], summary="List attendance",
            dependencies=[Depends(require("attendance", "view"))])
def list_attendance(
    db: DbSession,
    principal: CurrentPrincipal,
    period: PeriodQuery,
    client_id: int | None = None,
    coach_id: int | None = None,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Page[AttendanceRead]:
    start, end = month_bounds(period)

    filters = [Attendance.session_on >= start, Attendance.session_on <= end]
    if client_id is not None:
        filters.append(Attendance.client_id == client_id)
    if coach_id is not None:
        filters.append(Attendance.coach_id == coach_id)
    filters.extend(_scope(principal))

    stmt = select(Attendance).where(*filters)
    total = int(db.scalar(select(func.count()).select_from(Attendance).where(*filters)) or 0)
    rows = db.scalars(
        stmt.order_by(Attendance.session_on.desc(), Attendance.client_id)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page[AttendanceRead](
        items=[AttendanceRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=AttendanceRead, status_code=status.HTTP_201_CREATED,
             summary="Record one client's attendance",
             dependencies=[Depends(require("attendance", "manage"))])
def record(payload: AttendanceCreate, db: DbSession, principal: CurrentPrincipal) -> AttendanceRead:
    """
    Insert or update, keyed on (client, day).

    The grid saves the same cell more than once while a user changes their
    mind, so an upsert is the honest contract; a plain insert would answer 409
    on a legitimate second edit.
    """
    if payload.status not in VALID_STATUS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of {', '.join(VALID_STATUS)}",
        )
    ensure_client_scope(db, principal, payload.client_id)
    if db.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    row = db.scalar(
        select(Attendance).where(
            Attendance.client_id == payload.client_id,
            Attendance.session_on == payload.session_on,
        )
    )
    if row is None:
        row = Attendance(client_id=payload.client_id, session_on=payload.session_on)
    row.coach_id = payload.coach_id
    row.status = payload.status
    row.note = payload.note
    row.recorded_by = principal.id
    db.add(row)
    db.commit()
    db.refresh(row)
    return AttendanceRead.model_validate(row)


@router.delete("/{attendance_id}", response_model=Ok, summary="Undo one attendance row",
               dependencies=[Depends(require("attendance", "manage"))])
def remove(attendance_id: int, db: DbSession) -> Ok:
    row = db.get(Attendance, attendance_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance row not found")
    db.delete(row)
    db.commit()
    return Ok(detail="Attendance row removed")