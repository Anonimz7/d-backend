from __future__ import annotations
"""
/clients - menu: Klien.

Route order matters. ``/clients/export`` is declared before ``/clients/{id}``
so the literal segment wins over the path parameter.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/clients.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from ..models import (
    CLIENT_ACTIVE,
    CLIENT_ARCHIVED,
    Client,
    ClientSchedule,
    Coach,
    Enrollment,
)
from ..schemas.client import (
    ArchiveRequest,
    ClientCreate,
    ClientDetail,
    ClientPatch,
    ClientRead,
    EnrollmentCreate,
    EnrollmentRead,
)
from ..schemas.common import Ok, Page
from ..deps import CurrentPrincipal, DbSession, ensure_client_scope, require

router = APIRouter(prefix="/clients", tags=["clients"])


def _get(db, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


def _filter(db, principal: CurrentPrincipal, *, q, status_filter, coach_id, include_archived):
    stmt = select(Client).options(selectinload(Client.enrollments))
    count_stmt = select(func.count()).select_from(Client)

    filters = []
    if q:
        like = f"%{q.strip().lower()}%"
        filters.append(or_(func.lower(Client.name).like(like), Client.phone.like(f"%{q.strip()}%")))
    if status_filter:
        filters.append(Client.status == status_filter)
    elif not include_archived:
        filters.append(Client.status == CLIENT_ACTIVE)
    if coach_id is not None:
        filters.append(Client.coach_id == coach_id)

    # Data scope: a client sees only itself, a coach only their roster.
    if not principal.may_see_all_clients():
        if principal.client_id is not None:
            filters.append(Client.id == principal.client_id)
        elif principal.coach_id is not None:
            filters.append(Client.coach_id == principal.coach_id)
        else:
            filters.append(Client.id == -1)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)
    return stmt, count_stmt


@router.get("", response_model=Page[ClientRead], summary="List clients",
            dependencies=[Depends(require("clients", "view"))])
def list_clients(
    db: DbSession,
    principal: CurrentPrincipal,
    q: str | None = Query(None, max_length=120),
    status_filter: str | None = Query(None, alias="status", pattern=r"^(aktif|arsip)$"),
    coach_id: int | None = None,
    include_archived: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ClientRead]:
    stmt, count_stmt = _filter(db, principal, q=q, status_filter=status_filter, coach_id=coach_id,
                              include_archived=include_archived)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(stmt.order_by(Client.name).limit(limit).offset(offset)).unique().all()
    return Page[ClientRead](
        items=[ClientRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.get("/export", summary="CSV export (menu: Klien -> Ekspor)",
            dependencies=[Depends(require("clients", "export"))])
def export_csv(
    db: DbSession,
    principal: CurrentPrincipal,
    q: str | None = Query(None, max_length=120),
    status_filter: str | None = Query(None, alias="status", pattern=r"^(aktif|arsip)$"),
    coach_id: int | None = None,
) -> Response:
    stmt, _ = _filter(db, principal, q=q, status_filter=status_filter, coach_id=coach_id,
                      include_archived=status_filter == CLIENT_ARCHIVED)
    rows = db.scalars(stmt.order_by(Client.name)).unique().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "nama", "telepon", "email", "status", "bergabung", "coach_id", "catatan"])
    for c in rows:
        writer.writerow([c.id, c.name, c.phone or "", c.email or "", c.status, c.joined_on.isoformat(),
                         c.coach_id or "", (c.notes or "").replace("\n", " ")])
    # BOM so Excel reads the UTF-8 accents correctly.
    body = "\ufeff" + buf.getvalue()
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="n6-clients.csv"'},
    )


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED, summary="Create a client",
             dependencies=[Depends(require("clients", "create"))])
def create_client(payload: ClientCreate, db: DbSession, principal: CurrentPrincipal) -> ClientRead:
    # A coach may only enrol a client on their own roster.
    if not principal.may_see_all_clients():
        if principal.coach_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account cannot create client records",
            )
        payload = payload.model_copy(update={"coach_id": principal.coach_id})

    client = Client(
        name=payload.name.strip(),
        phone=payload.phone,
        email=payload.email,
        gender=payload.gender,
        birth_date=payload.birth_date,
        address=payload.address,
        notes=payload.notes,
        joined_on=payload.joined_on,
        coach_id=payload.coach_id,
        status=CLIENT_ACTIVE,
    )
    db.add(client)
    db.flush()

    if payload.program_id is not None:
        db.add(
            Enrollment(
                client_id=client.id,
                program_id=payload.program_id,
                coach_id=payload.coach_id,
                start_on=payload.joined_on,
                weeks=payload.weeks or 4,
                price_paid=payload.price_paid or 0,
            )
        )

    db.commit()
    db.refresh(client)
    return ClientRead.model_validate(client)


@router.get("/{client_id}", response_model=ClientDetail, summary="Client detail (modal on Klien)",
            dependencies=[Depends(require("clients", "view"))])
def get_client(client_id: int, db: DbSession, principal: CurrentPrincipal) -> ClientDetail:
    ensure_client_scope(db, principal, client_id)
    client = _get(db, client_id)
    coach = db.get(Coach, client.coach_id) if client.coach_id else None
    slots = db.scalars(
        select(ClientSchedule).where(ClientSchedule.client_id == client_id).order_by(
            ClientSchedule.weekday, ClientSchedule.start_time
        )
    ).all()
    detail = ClientDetail.model_validate(client)
    detail.coach_name = coach.name if coach else None
    detail.active_enrollments = [EnrollmentRead.model_validate(e) for e in client.enrollments]
    detail.schedule = [
        {
            "weekday": s.weekday,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "location": s.location,
            "training_category": s.training_category,
        }
        for s in slots
    ]
    return detail


@router.patch("/{client_id}", response_model=ClientRead, summary="Edit a client",
              dependencies=[Depends(require("clients", "update"))])
def update_client(client_id: int, payload: ClientPatch, db: DbSession,
                  principal: CurrentPrincipal) -> ClientRead:
    ensure_client_scope(db, principal, client_id)
    client = _get(db, client_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    client.updated_at = datetime.now(timezone.utc)
    db.add(client)
    db.commit()
    db.refresh(client)
    return ClientRead.model_validate(client)


@router.post("/{client_id}/archive", response_model=ClientRead, summary="Archive or restore a client",
             dependencies=[Depends(require("clients", "archive"))])
def archive_client(client_id: int, payload: ArchiveRequest, db: DbSession,
                   principal: CurrentPrincipal) -> ClientRead:
    ensure_client_scope(db, principal, client_id)
    client = _get(db, client_id)

    if payload.archived:
        client.status = CLIENT_ARCHIVED
        client.archived_on = payload.archived_on
        if payload.reason and not client.notes:
            client.notes = payload.reason
    else:
        client.status = CLIENT_ACTIVE
        client.archived_on = None

    client.updated_at = datetime.now(timezone.utc)
    db.add(client)
    db.commit()
    db.refresh(client)
    return ClientRead.model_validate(client)


@router.delete("/{client_id}", response_model=Ok, summary="Delete a client",
               dependencies=[Depends(require("clients", "update"))])
def delete_client(client_id: int, db: DbSession, principal: CurrentPrincipal) -> Ok:
    ensure_client_scope(db, principal, client_id)
    client = _get(db, client_id)
    name = client.name
    db.delete(client)
    db.commit()
    return Ok(detail=f"{name} deleted together with their schedule and enrolments")


# ----------------------------------------------------------------- enrolments
@router.post("/{client_id}/enrollments", response_model=EnrollmentRead,
             status_code=status.HTTP_201_CREATED, summary="Register a program for a client",
             dependencies=[Depends(require("clients", "create"))])
def add_enrollment(client_id: int, payload: EnrollmentCreate, db: DbSession,
                   principal: CurrentPrincipal) -> EnrollmentRead:
    ensure_client_scope(db, principal, client_id)
    _get(db, client_id)
    enrollment = Enrollment(
        client_id=client_id,
        program_id=payload.program_id,
        coach_id=payload.coach_id,
        start_on=payload.start_on,
        weeks=payload.weeks,
        price_paid=payload.price_paid,
        payment_status=payload.payment_status,
        custom_label=payload.custom_label,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return EnrollmentRead.model_validate(enrollment)