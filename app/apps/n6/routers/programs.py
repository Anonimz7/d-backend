from __future__ import annotations
"""
/programs - the catalogue behind Harga & Program and the head coach's
Buat Program menu.

Publishing is separated from editing because a draft is what a head coach
iterates on and a published program is what admin can sell.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/programs.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..models import PROGRAM_DRAFT, PROGRAM_PUBLISHED, PriceItem, Program
from ..schemas.common import Page
from ..schemas.program import ProgramCreate, ProgramPatch, ProgramRead
from ..deps import CurrentPrincipal, DbSession, require

router = APIRouter(prefix="/programs", tags=["programs"])


def _get(db, program_id: int) -> Program:
    program = db.scalar(
        select(Program).options(selectinload(Program.prices)).where(Program.id == program_id)
    )
    if program is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program


def _replace_prices(db, program: Program, items) -> None:
    for row in list(program.prices):
        db.delete(row)
    db.flush()
    for position, item in enumerate(items):
        db.add(
            PriceItem(
                program_id=program.id,
                label=item.label,
                unit=item.unit,
                price=item.price,
                position=item.position if item.position is not None else position,
            )
        )


@router.get("", response_model=Page[ProgramRead], summary="List programs",
            dependencies=[Depends(require("programs", "view"))])
def list_programs(
    db: DbSession,
    q: str | None = Query(None, max_length=120),
    status_filter: str | None = Query(None, alias="status", pattern=r"^(draft|published)$"),
    category: str | None = Query(None, max_length=80),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ProgramRead]:
    stmt = select(Program).options(selectinload(Program.prices))
    count_stmt = select(func.count()).select_from(Program)

    filters = []
    if q:
        like = f"%{q.strip().lower()}%"
        filters.append(func.lower(Program.name).like(like))
    if status_filter:
        filters.append(Program.status == status_filter)
    if category:
        filters.append(Program.category == category)
    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(Program.category, Program.name).limit(limit).offset(offset)
    ).unique().all()
    return Page[ProgramRead](
        items=[ProgramRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.get("/{program_id}", response_model=ProgramRead, summary="Program detail",
            dependencies=[Depends(require("programs", "view"))])
def get_program(program_id: int, db: DbSession) -> ProgramRead:
    return ProgramRead.model_validate(_get(db, program_id))


@router.post("", response_model=ProgramRead, status_code=status.HTTP_201_CREATED,
             summary="Create a draft program",
             dependencies=[Depends(require("programs", "manage"))])
def create_program(payload: ProgramCreate, db: DbSession, principal: CurrentPrincipal) -> ProgramRead:
    # ProgramCreate carries an optional id so PUT /pricing can update in place.
    # POST has no path id, so a body that brings its own is a caller mistake -
    # accepting it would let a stale screen overwrite an unrelated row.
    if payload.id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="POST /programs always creates; use PATCH /programs/{id} to edit",
        )

    clash = db.scalar(
        select(Program).where(
            func.lower(Program.name) == payload.name.strip().lower(),
            func.lower(func.coalesce(Program.category, "")) == (payload.category or "").lower(),
        )
    )
    if clash is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Program with that name already exists")

    program = Program(
        name=payload.name.strip(),
        category=payload.category,
        duration_weeks=payload.duration_weeks,
        meeting_per_week=payload.meeting_per_week,
        price=payload.price,
        notes=payload.notes,
        template=payload.template,
        status=PROGRAM_DRAFT,
    )
    db.add(program)
    db.flush()
    _replace_prices(db, program, payload.prices)
    db.commit()
    db.refresh(program)
    return ProgramRead.model_validate(program)


@router.patch("/{program_id}", response_model=ProgramRead, summary="Edit a program",
              dependencies=[Depends(require("programs", "manage"))])
def update_program(program_id: int, payload: ProgramPatch, db: DbSession) -> ProgramRead:
    """
    `ProgramPatch` has no `status` field, so this cannot publish.

    That is deliberate: `POST /programs/{id}/publish` is the only way a draft
    goes on sale, and it is gated separately. If PATCH could set the status, the
    publish action would be a formality.
    """
    program = _get(db, program_id)
    fields = payload.model_dump(exclude_unset=True, exclude={"prices"})
    for field, value in fields.items():
        setattr(program, field, value)
    if payload.prices is not None:
        _replace_prices(db, program, payload.prices)
    program.updated_at = datetime.now(timezone.utc)
    db.add(program)
    db.commit()
    db.refresh(program)
    return ProgramRead.model_validate(program)


@router.post("/{program_id}/publish", response_model=ProgramRead, summary="Publish a program",
             dependencies=[Depends(require("programs", "publish"))])
def publish_program(program_id: int, db: DbSession) -> ProgramRead:
    """
    Draft -> published, on the head coach's own say-so.

    Idempotent: publishing an already-published program returns it unchanged
    rather than moving `published_on` to today, so the date on the Harga &
    Program list keeps meaning "since when has this been sellable".
    """
    program = _get(db, program_id)
    if program.status != PROGRAM_PUBLISHED:
        program.status = PROGRAM_PUBLISHED
        program.published_on = datetime.now(timezone.utc).date()
        program.updated_at = datetime.now(timezone.utc)
        db.add(program)
        db.commit()
        db.refresh(program)
    return ProgramRead.model_validate(program)