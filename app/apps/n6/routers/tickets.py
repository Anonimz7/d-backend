from __future__ import annotations
"""
/tickets - menu: Tiket & Keluhan.

`GET /tickets/{id}` is deliberately absent: the dashboard's ticket list already
carries the detail it renders, and adding a second read path would let the two
disagree about what a ticket looks like.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/tickets.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..models import TICKET_CLOSED, TICKET_OPEN, TICKET_REPLIED, Ticket, TicketReply
from ..schemas.common import Ok, Page
from ..schemas.support import ReplyRequest, TicketClose, TicketRead
from ..deps import CurrentPrincipal, DbSession, ensure_client_scope, require

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _get(db, ticket_id: int) -> Ticket:
    ticket = db.scalar(
        select(Ticket).options(selectinload(Ticket.replies)).where(Ticket.id == ticket_id)
    )
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


def _read(ticket: Ticket) -> TicketRead:
    out = TicketRead.model_validate(ticket)
    out.reply_count = len(ticket.replies)
    out.last_reply_at = ticket.replies[-1].created_at if ticket.replies else None
    return out


@router.get("", response_model=Page[TicketRead], summary="List tickets",
            dependencies=[Depends(require("tickets", "view"))])
def list_tickets(
    db: DbSession,
    principal: CurrentPrincipal,
    status_filter: str | None = Query(None, alias="status", pattern=r"^(terbuka|dibalas|selesai)$"),
    client_id: int | None = None,
    priority: str | None = Query(None, pattern=r"^(rendah|sedang|tinggi)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[TicketRead]:
    stmt = select(Ticket).options(selectinload(Ticket.replies))
    count_stmt = select(func.count()).select_from(Ticket)

    filters = []
    if status_filter:
        filters.append(Ticket.status == status_filter)
    elif status_filter is None:
        filters.append(Ticket.status != TICKET_CLOSED)
    if client_id is not None:
        filters.append(Ticket.client_id == client_id)
    if priority:
        filters.append(Ticket.priority == priority)
    if not principal.may_see_all_clients():
        if principal.client_id is not None:
            filters.append(Ticket.client_id == principal.client_id)
        else:
            filters.append(Ticket.client_id == -1)

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        stmt.order_by(Ticket.id.desc()).limit(limit).offset(offset)
    ).unique().all()
    return Page[TicketRead](
        items=[_read(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.get("/{ticket_id}/replies", summary="The conversation on one ticket",
            dependencies=[Depends(require("tickets", "view"))])
def list_replies(ticket_id: int, db: DbSession, principal: CurrentPrincipal) -> list[dict]:
    ticket = _get(db, ticket_id)
    ensure_client_scope(db, principal, ticket.client_id)
    return [
        {
            "id": r.id,
            "author_id": r.author_id,
            "body": r.body,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in ticket.replies
    ]


@router.post("/{ticket_id}/reply", response_model=TicketRead, summary="Answer a ticket",
             dependencies=[Depends(require("tickets", "reply"))])
def reply(ticket_id: int, payload: ReplyRequest, db: DbSession,
          principal: CurrentPrincipal) -> TicketRead:
    ticket = _get(db, ticket_id)
    if ticket.status == TICKET_CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ticket is closed; open a new one instead",
        )

    db.add(TicketReply(ticket_id=ticket.id, author_id=principal.id, body=payload.body))
    # Reopening from 'terbuka' to 'dibalas' is what drives the sidebar badge.
    if ticket.status == TICKET_OPEN:
        ticket.status = TICKET_REPLIED
    db.add(ticket)
    db.commit()
    # Re-read rather than db.refresh(): the reply count and last-reply stamp in
    # TicketRead come from the replies collection, which refresh() does not
    # reload after a collection changed behind it.
    return _read(_get(db, ticket_id))


@router.post("/{ticket_id}/close", response_model=Ok, summary="Close a ticket",
             dependencies=[Depends(require("tickets", "close"))])
def close(ticket_id: int, payload: TicketClose, db: DbSession) -> Ok:
    ticket = _get(db, ticket_id)
    if ticket.status == TICKET_CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already closed on {ticket.closed_at}",
        )

    if payload.resolution:
        db.add(
            TicketReply(
                ticket_id=ticket.id,
                author_id=None,
                body=f"[ditutup] {payload.note or payload.resolution}",
            )
        )
    ticket.status = TICKET_CLOSED
    ticket.closed_at = datetime.now(timezone.utc)
    db.add(ticket)
    db.commit()
    return Ok(detail=f"Ticket #{ticket_id} closed")
