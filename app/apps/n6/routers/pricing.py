from __future__ import annotations
"""
/pricing - menu: Harga & Program.

GET returns the whole screen in one payload, because the dashboard keeps the
program catalogue and the standalone price list side by side. PUT takes both
back in one body, because the editor is a single save button.

PUT is a diff, not a wipe. An earlier draft deleted every Program row before
re-inserting the payload, which is the obvious way to write "replace" and the
wrong one: `Enrollment.program_id` points at those rows, so every enrolled
client would have been left pointing at nothing while the price screen looked
perfectly healthy. So rows carrying an `id` are updated in place, rows without
one are inserted, and a row missing from the body is deleted - refused with a
409 when somebody is still enrolled in it, because that is a decision for a
person and not for a save button.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/pricing.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from ..models import PROGRAM_PUBLISHED, Enrollment, PriceItem, Program
from ..schemas.program import (
    PriceItemIn,
    PriceItemRead,
    PricingRead,
    PricingWrite,
    ProgramRead,
)
from ..deps import DbSession, require

router = APIRouter(prefix="/pricing", tags=["pricing"])


def _apply_item(db, program_id: int | None, item: PriceItemIn, fallback: int) -> None:
    """Insert or update one price row, keeping an existing row's id."""
    if item.id is not None:
        row = db.get(PriceItem, item.id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Price row {item.id} no longer exists; reload the screen",
            )
    else:
        row = PriceItem(program_id=program_id)
        db.add(row)

    row.program_id = program_id
    row.label = item.label.strip()
    row.unit = item.unit
    row.price = item.price
    row.position = item.position if item.position is not None else fallback
    db.add(row)


@router.get("", response_model=PricingRead, summary="Program catalogue and price list",
            dependencies=[Depends(require("pricing", "view"))])
def read_pricing(db: DbSession) -> PricingRead:
    programs = db.scalars(select(Program).order_by(Program.category, Program.name)).unique().all()
    standalone = db.scalars(
        select(PriceItem).where(PriceItem.program_id.is_(None)).order_by(PriceItem.position, PriceItem.label)
    ).all()

    # "When did this screen last change": the newest stamp across everything it
    # shows. Null while the catalogue is still empty, which is honest.
    stamps = [p.updated_at for p in programs] + [i.updated_at for i in standalone]
    stamps = [s for s in stamps if s is not None]

    return PricingRead(
        programs=[ProgramRead.model_validate(p) for p in programs],
        standalone=[PriceItemRead.model_validate(i) for i in standalone],
        updated_at=max(stamps) if stamps else None,
    )


@router.put("", response_model=PricingRead, summary="Save the catalogue",
            dependencies=[Depends(require("pricing", "manage"))])
def write_pricing(payload: PricingWrite, db: DbSession) -> PricingRead:
    keep_program_ids = {p.id for p in payload.programs if p.id is not None}
    keep_item_ids = {i.id for p in payload.programs for i in p.prices if i.id is not None}
    keep_item_ids |= {i.id for i in payload.standalone if i.id is not None}

    # A program cannot be edited into a different program: an id belonging to
    # something else is a bug in the caller, and silently inserting a new row
    # under a stale id would produce a duplicate nobody asked for.
    claimed_ids = [p.id for p in payload.programs if p.id is not None]
    if len(claimed_ids) != len(set(claimed_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="the same program id appears twice",
        )

    # -------------------------------------------------------------- programs
    for program in payload.programs:
        if program.id is None:
            row = Program(name=program.name.strip())
        else:
            row = db.get(Program, program.id)
            if row is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Program {program.id} no longer exists; reload the screen",
                )

        row.name = program.name.strip()
        row.category = program.category
        row.duration_weeks = program.duration_weeks
        row.meeting_per_week = program.meeting_per_week
        row.price = program.price
        row.notes = program.notes
        row.template = program.template
        # A program saved through the price screen is already agreed with the
        # client, so it counts as published. Drafting lives in the head coach's
        # Buat Program menu, and `published_on` is left alone on a re-save so
        # the date keeps meaning "sellable since".
        if row.status != PROGRAM_PUBLISHED:
            row.status = PROGRAM_PUBLISHED
            row.published_on = datetime.now(timezone.utc).date()
        db.add(row)
        db.flush()
        # Program baru mendapat id setelah flush; masukkan ke keep agar
        # tidak ikut terhapus di bagian deletions di bawah.
        keep_program_ids.add(row.id)

        for position, item in enumerate(program.prices):
            _apply_item(db, row.id, item, position)

    # ------------------------------------------------------------- deletions
    doomed = db.scalars(select(Program).where(Program.id.notin_(keep_program_ids or {-1}))).all()
    for row in doomed:
        enrolled = int(
            db.scalar(
                select(func.count()).select_from(Enrollment).where(Enrollment.program_id == row.id)
            )
            or 0
        )
        if enrolled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"'{row.name}' is still on {enrolled} enrolment(s). "
                    "Move those clients to another program first."
                ),
            )
        db.delete(row)
    db.flush()

    for item in db.scalars(select(PriceItem)).all():
        if item.id not in keep_item_ids:
            db.delete(item)

    for position, item in enumerate(payload.standalone):
        _apply_item(db, None, item, position)

    db.commit()
    return read_pricing(db)