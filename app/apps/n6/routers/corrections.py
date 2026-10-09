from __future__ import annotations
"""
/corrections - menu Koreksi (head coach).

A correction is a proposed change to a client's own record, raised by the head
coach on the client's behalf and then resolved. `apply_to_client` decides
whether resolving also writes the value onto the client row; that flag is the
whole reason this endpoint exists rather than a plain PATCH on /clients.

Admin and coach can read but not resolve: the matrix grants them
``corrections.view`` only, so `corrections.manage` is what makes the buttons
appear and what makes the route answer.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/corrections.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from ..models import CORRECTION_OPEN, CORRECTION_RESOLVED, Client, Correction
from ..schemas.common import Page
from ..schemas.support import CorrectionCreate, CorrectionRead, CorrectionResolve
from ..deps import CurrentPrincipal, DbSession, require

router = APIRouter(prefix="/corrections", tags=["corrections"])

#: Fields a correction is allowed to propose. Anything else is a structural
#: change (tier, status, money) and belongs on the record it belongs to, not in
#: a request queue.
EDITABLE = {
    "name": "name",
    "phone": "phone",
    "email": "email",
    "gender": "gender",
    "birth_date": "birth_date",
    "address": "address",
    "notes": "notes",
}


@router.get("", response_model=Page[CorrectionRead], summary="List corrections",
            dependencies=[Depends(require("corrections", "view"))])
def list_corrections(
    db: DbSession,
    principal: CurrentPrincipal,
    status_filter: str | None = Query(None, alias="status",
                                       pattern=r"^(menunggu|selesai)$"),
    client_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[CorrectionRead]:
    filters = []
    if status_filter:
        filters.append(Correction.status == status_filter)
    else:
        # The Koreksi screen shows the queue, not the archive.
        filters.append(Correction.status == CORRECTION_OPEN)
    if client_id is not None:
        filters.append(Correction.client_id == client_id)
    if not principal.may_see_all_clients() and principal.coach_id is not None:
        filters.append(Correction.client_id.in_(
            select(Client.id).where(Client.coach_id == principal.coach_id)
        ))

    stmt = select(Correction)
    total = int(db.scalar(select(func.count()).select_from(Correction).where(*filters)) or 0)
    rows = db.scalars(
        stmt.where(*filters).order_by(Correction.id.desc()).limit(limit).offset(offset)
    ).all()
    return Page[CorrectionRead](
        items=[CorrectionRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CorrectionRead, status_code=status.HTTP_201_CREATED,
             summary="Raise a correction",
             dependencies=[Depends(require("corrections", "manage"))])
def create_correction(
    payload: CorrectionCreate, db: DbSession, principal: CurrentPrincipal
) -> CorrectionRead:
    if payload.field not in EDITABLE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{payload.field}' is not correctable; allowed: {', '.join(sorted(EDITABLE))}",
        )
    if payload.client_id is None or db.get(Client, payload.client_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown client")

    # before_value is captured now, not at resolve time, so the queue records
    # what the field held when the correction was raised rather than when it
    # was dealt with - which is the only version that makes the diff readable.
    current = getattr(db.get(Client, payload.client_id), EDITABLE[payload.field], None)
    row = Correction(
        client_id=payload.client_id,
        field=payload.field,
        before_value=None if current is None else str(current),
        after_value=payload.after_value,
        reason=payload.reason,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CorrectionRead.model_validate(row)


@router.post("/{correction_id}/resolve", response_model=CorrectionRead,
             summary="Resolve a correction",
             dependencies=[Depends(require("corrections", "manage"))])
def resolve(
    correction_id: int, payload: CorrectionResolve, db: DbSession,
    principal: CurrentPrincipal,
) -> CorrectionRead:
    row = db.get(Correction, correction_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Correction not found")
    if row.status != CORRECTION_OPEN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already resolved on {row.resolved_at}",
        )

    if payload.apply_to_client and row.after_value is not None:
        client = db.get(Client, row.client_id)
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        setattr(client, EDITABLE[row.field], row.after_value)
        db.add(client)

    row.status = CORRECTION_RESOLVED
    row.resolution_note = payload.resolution_note
    row.resolved_by = principal.id
    row.resolved_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return CorrectionRead.model_validate(row)