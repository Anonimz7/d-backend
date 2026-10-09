from __future__ import annotations
"""
/athletes - menu Atlet Binaan (head coach only).

One row per client per month, stored as AthleteNote. `PUT /athletes/{client_id}`
is an upsert keyed on (client_id, period): the screen edits all seven fields of
one row and saves in a single click, so there is no create/read split here.
The path parameter is the *client*, not the note, because the note id does not
exist until the first save and the screen never shows it.

Rows for reading, with attendance folded in, come from /monitoring/clients.
This router owns only the write, which keeps the "who may set targets" answer
in exactly one place.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/athletes.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from ..period import current_month
from ..models import CLIENT_ACTIVE, AthleteNote, Client
from ..schemas.common import Ok, Page
from ..schemas.support import AthleteRead, AthleteUpdate
from ..deps import DbSession, PeriodQuery, require

router = APIRouter(prefix="/athletes", tags=["athletes"])

#: The seven fields a coach may set. Listed explicitly so a stray key in the
#: body is a 422 rather than a silently ignored attribute.
FIELDS = (
    "pace_target",
    "hr_target",
    "intensity",
    "note",
    "flag_kehadiran",
    "flag_ordinal",
    "flag_komisi",
)


def _read(note: AthleteNote, client: Client) -> AthleteRead:
    return AthleteRead(
        id=note.id,
        client_id=client.id,
        client_name=client.name,
        period=note.period or "",
        pace_target=note.pace_target,
        hr_target=note.hr_target,
        intensity=note.intensity,
        note=note.note,
        flag_kehadiran=note.flag_kehadiran,
        flag_ordinal=note.flag_ordinal,
        flag_komisi=note.flag_komisi,
    )


@router.get("", response_model=Page[AthleteRead], summary="Athlete rows for one month",
            dependencies=[Depends(require("athletes", "view"))])
def list_athletes(
    db: DbSession,
    period: PeriodQuery,
    client_id: int | None = None,
    coach_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[AthleteRead]:
    """
    Only clients who already have a note this month.

    Unlike /monitoring/clients, which returns the whole roster including
    clients nobody has tracked yet. The Atlet screen is the head coach's own
    working list, so an untracked client is not on it.
    """
    filters = [AthleteNote.period == period]
    if client_id is not None:
        filters.append(AthleteNote.client_id == client_id)
    if coach_id is not None:
        filters.append(Client.coach_id == coach_id)

    total = int(
        db.scalar(select(func.count()).select_from(AthleteNote).where(*filters)) or 0
    )
    rows = db.execute(
        select(AthleteNote, Client)
        .join(Client, Client.id == AthleteNote.client_id)
        .where(*filters, Client.status == CLIENT_ACTIVE)
        .order_by(Client.name)
        .limit(limit)
        .offset(offset)
    ).all()
    return Page[AthleteRead](
        items=[_read(note, client) for note, client in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.put("/{client_id}", response_model=AthleteRead,
            summary="Set this month's targets and flags for one client",
            dependencies=[Depends(require("athletes", "manage"))])
def upsert_athlete(client_id: int, payload: AthleteUpdate, db: DbSession) -> AthleteRead:
    """
    Upsert on (client_id, period).

    A partial body leaves the omitted fields alone rather than nulling them:
    the screen saves the flag a coach just clicked without re-sending the note
    they typed last week, and wiping it would lose their work.
    """
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    body = payload.model_dump(exclude_unset=True)
    unknown = sorted(set(body) - set(FIELDS) - {"period"})
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"unknown field(s): {', '.join(unknown)}",
        )

    period = body.get("period") or payload.period or current_month()
    row = db.scalar(
        select(AthleteNote).where(
            AthleteNote.client_id == client_id, AthleteNote.period == period
        )
    )
    if row is None:
        row = AthleteNote(client_id=client_id, period=period)
    row.period = period
    for field in FIELDS:
        if field in body:
            setattr(row, field, body[field])

    db.add(row)
    db.commit()
    db.refresh(row)
    return _read(row, client)


@router.delete("/{client_id}", response_model=Ok, summary="Drop a client's month row",
               dependencies=[Depends(require("athletes", "manage"))])
def remove_athlete(client_id: int, db: DbSession, period: PeriodQuery) -> Ok:
    row = db.scalar(
        select(AthleteNote).where(
            AthleteNote.client_id == client_id, AthleteNote.period == period
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No athlete row for that client and month",
        )
    db.delete(row)
    db.commit()
    return Ok(detail=f"Athlete row for {period} removed")