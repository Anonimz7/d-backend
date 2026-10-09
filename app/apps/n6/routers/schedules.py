from __future__ import annotations
"""
/schedules - menus: Jadwal Coach and Jadwal Klien.

`/schedules/coach` is declared before `/schedules/coach/requests` is harmless
here, but keep the literal segments ahead of the parameterised ones for the
same reason as in clients.py.

Every write is a full replace: the dashboard saves the whole weekly template in
one go, so a diffing endpoint would only add a way for the two to disagree.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/schedules.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ..models import (
    REQUEST_APPROVED,
    REQUEST_PENDING,
    REQUEST_REJECTED,
    Client,
    ClientSchedule,
    Coach,
    CoachScheduleSlot,
    ScheduleRequest,
)
from ..schemas.common import Ok, Page
from ..schemas.schedule import (
    ClientScheduleRead,
    ClientScheduleWrite,
    CoachScheduleRead,
    CoachScheduleWrite,
    RequestDecision,
    ScheduleRequestRead,
    SlotIn,
)
from ..deps import CurrentPrincipal, DbSession, Principal, ensure_client_scope, require

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _slot_payload(slot: SlotIn) -> dict:
    return slot.model_dump()


def _slots(rows) -> list[SlotIn]:
    return [
        SlotIn(
            weekday=r.weekday,
            start_time=r.start_time,
            end_time=r.end_time,
            location=r.location,
            training_category=r.training_category,
            note=r.note,
            active=r.active,
        )
        for r in rows
    ]


# ------------------------------------------------------------- coach template
@router.get("/coach", response_model=CoachScheduleRead, summary="A coach's weekly template",
            dependencies=[Depends(require("coach_schedule", "view"))])
def get_coach_schedule(
    db: DbSession,
    principal: CurrentPrincipal,
    coach_id: int | None = Query(None, description="Omit to read your own schedule"),
) -> CoachScheduleRead:
    target = _resolve_coach(principal, coach_id)
    rows = db.scalars(
        select(CoachScheduleSlot)
        .where(CoachScheduleSlot.coach_id == target)
        .order_by(CoachScheduleSlot.weekday, CoachScheduleSlot.start_time)
    ).all()
    coach = db.get(Coach, target)
    return CoachScheduleRead(
        coach_id=target, coach_name=coach.name if coach else None, slots=_slots(rows)
    )


@router.put("/coach", response_model=CoachScheduleRead, summary="Replace a coach's weekly template",
            dependencies=[Depends(require("coach_schedule", "manage"))])
def save_coach_schedule(payload: CoachScheduleWrite, db: DbSession,
                        principal: CurrentPrincipal) -> CoachScheduleRead:
    target = _resolve_coach(principal, payload.coach_id)

    existing = db.scalars(select(CoachScheduleSlot).where(CoachScheduleSlot.coach_id == target)).all()
    for row in existing:
        db.delete(row)
    db.flush()

    for slot in payload.slots:
        db.add(CoachScheduleSlot(coach_id=target, **_slot_payload(slot)))

    db.commit()
    return get_coach_schedule(db, principal, target)


# ----------------------------------------------------------- change requests
@router.get("/coach/requests", response_model=Page[ScheduleRequestRead],
            summary="List change requests",
            dependencies=[Depends(require("coach_schedule", "requests_view"))])
def list_requests(
    db: DbSession,
    principal: CurrentPrincipal,
    status_filter: str | None = Query(None, alias="status", pattern=r"^(menunggu|disetujui|ditolak)$"),
    coach_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ScheduleRequestRead]:
    stmt = select(ScheduleRequest)
    count_stmt = select(func.count()).select_from(ScheduleRequest)
    filters = []
    if status_filter:
        filters.append(ScheduleRequest.status == status_filter)
    if coach_id is not None:
        filters.append(ScheduleRequest.coach_id == coach_id)
    elif not principal.may_see_all_clients() and principal.coach_id is not None:
        filters.append(ScheduleRequest.coach_id == principal.coach_id)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(ScheduleRequest.requested_on.desc(), ScheduleRequest.id.desc()).limit(limit).offset(offset)
    ).all()
    return Page[ScheduleRequestRead](
        items=[ScheduleRequestRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


class ScheduleRequestCreate(BaseModel):
    type: str = Field(pattern=r"^(reschedule|cuti)$")
    date: date
    reason: str = Field(min_length=1, max_length=500)


@router.post("/coach/requests", response_model=ScheduleRequestRead,
             summary="Submit a change request (coach)",
             dependencies=[Depends(require("coach_schedule", "requests_view"))])
def create_request(payload: ScheduleRequestCreate, db: DbSession,
                   principal: CurrentPrincipal) -> ScheduleRequestRead:
    # Coach mengajukan cuti/reschedule. client_id null (butuh ALTER TABLE
    # agar kolom nullable) — untuk reschedule sesi tertentu, client_id
    # diisi via PUT oleh admin/headcoach saat memproses.
    row = ScheduleRequest(
        client_id=None,  # type: ignore — kolom akan dibuat nullable
        coach_id=principal.coach_id,
        requested_on=payload.date,
        reason=f"[{payload.type}] {payload.reason}",
        status=REQUEST_PENDING,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ScheduleRequestRead.model_validate(row)


@router.put("/coach/requests/{request_id}", response_model=ScheduleRequestRead,
            summary="Approve or reject a change request",
            dependencies=[Depends(require("coach_schedule", "requests"))])
def decide_request(request_id: int, payload: RequestDecision, db: DbSession,
                   principal: CurrentPrincipal) -> ScheduleRequestRead:
    request = db.get(ScheduleRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if request.status != REQUEST_PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request was already {request.status}",
        )

    request.status = REQUEST_APPROVED if payload.status == "disetujui" else REQUEST_REJECTED
    request.decision_note = payload.decision_note
    request.decided_by = principal.id
    request.decided_at = datetime.now(timezone.utc)

    if payload.status == "disetujui" and (payload.new_start_time or payload.new_weekday):
        _apply_move(db, request, payload)

    db.add(request)
    db.commit()
    db.refresh(request)
    return ScheduleRequestRead.model_validate(request)


def _apply_move(db, request: ScheduleRequest, payload: RequestDecision) -> None:
    """Move the approved session onto the new slot, or drop it if none exists."""
    weekday = payload.new_weekday
    start_time = payload.new_start_time or request.current_start
    if weekday is None or start_time is None:
        return

    target = db.scalar(
        select(ClientSchedule).where(
            ClientSchedule.client_id == request.client_id,
            ClientSchedule.weekday == weekday,
            ClientSchedule.start_time == start_time,
        )
    )
    if target is None:
        target = ClientSchedule(client_id=request.client_id, weekday=weekday, start_time=start_time)
    target.active = True
    db.add(target)


# ------------------------------------------------------------ client schedule
@router.get("/clients", response_model=Page[ClientScheduleRead],
            summary="List all client schedules",
            dependencies=[Depends(require("client_schedule", "view"))])
def list_client_schedules(
    db: DbSession,
    principal: CurrentPrincipal,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ClientScheduleRead]:
    # Ambil semua client yang punya jadwal, dengan pagination
    # Untuk setiap client, ambil slots-nya
    client_ids = db.scalars(
        select(ClientSchedule.client_id)
        .distinct()
        .order_by(ClientSchedule.client_id)
        .limit(limit)
        .offset(offset)
    ).all()

    total = int(db.scalar(
        select(func.count(func.distinct(ClientSchedule.client_id)))
    ) or 0)

    items = []
    for cid in client_ids:
        client = db.get(Client, cid)
        rows = db.scalars(
            select(ClientSchedule)
            .where(ClientSchedule.client_id == cid)
            .order_by(ClientSchedule.weekday, ClientSchedule.start_time)
        ).all()
        items.append(ClientScheduleRead(
            client_id=cid,
            client_name=client.name if client else None,
            slots=_slots(rows),
        ))

    return Page[ClientScheduleRead](items=items, total=total, limit=limit, offset=offset)


@router.get("/clients/{client_id}", response_model=ClientScheduleRead,
            summary="A client's weekly plan",
            dependencies=[Depends(require("client_schedule", "view"))])
def get_client_schedule(client_id: int, db: DbSession, principal: CurrentPrincipal) -> ClientScheduleRead:
    ensure_client_scope(db, principal, client_id)
    client = db.get(Client, client_id)
    rows = db.scalars(
        select(ClientSchedule)
        .where(ClientSchedule.client_id == client_id)
        .order_by(ClientSchedule.weekday, ClientSchedule.start_time)
    ).all()
    return ClientScheduleRead(
        client_id=client_id, client_name=client.name if client else None, slots=_slots(rows)
    )


@router.put("/clients/{client_id}", response_model=ClientScheduleRead,
            summary="Replace a client's weekly plan",
            dependencies=[Depends(require("client_schedule", "manage"))])
def save_client_schedule(client_id: int, payload: ClientScheduleWrite, db: DbSession,
                         principal: CurrentPrincipal) -> ClientScheduleRead:
    ensure_client_scope(db, principal, client_id)
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    existing = db.scalars(select(ClientSchedule).where(ClientSchedule.client_id == client_id)).all()
    for row in existing:
        db.delete(row)
    db.flush()

    for slot in payload.slots:
        db.add(ClientSchedule(client_id=client_id, **_slot_payload(slot)))

    db.commit()
    return get_client_schedule(client_id, db, principal)


@router.delete("/coach/requests/{request_id}", response_model=Ok,
               summary="Withdraw a change request",
               dependencies=[Depends(require("coach_schedule", "view"))])
def withdraw_request(request_id: int, db: DbSession, principal: CurrentPrincipal) -> Ok:
    """
    Only the raiser may withdraw, and only while it is still pending.

    The `coach_schedule.view` gate already keeps a client off this route - the
    client tier file leaves coach_schedule empty - so the ownership check below
    is the second lock rather than the only one. It matters if a deployment
    later widens that action list: withdrawing a request an admin has already
    read, or one a different coach raised, is not something a view permission
    should authorise.
    """
    request = db.get(ScheduleRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if not principal.may_see_all_clients() and request.client_id != principal.client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")
    if request.status != REQUEST_PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Request was already {request.status}"
        )
    db.delete(request)
    db.commit()
    return Ok(detail="Request withdrawn")


def _resolve_coach(principal: Principal, coach_id: int | None) -> int:
    """A coach reads and writes their own template; wider roles may name one."""
    if coach_id is None:
        if principal.coach_id is not None:
            return int(principal.coach_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="coach_id is required for this account"
        )
    if not principal.may_see_all_clients() and principal.coach_id != int(coach_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="A coach may only edit their own template"
        )
    return int(coach_id)