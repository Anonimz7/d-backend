from __future__ import annotations
"""
/messages - menu: Pesan.

A thread is a plain string key rather than a table, because the dashboard's
internal chat groups by role pair (`admin`, `owner`, `coach:3`) and by client
(`client:12`). Deriving the key in one place keeps the unread badge counting
the same rows the list returns.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/messages.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select

from ..models import Account, Message
from ..schemas.common import Ok, Page
from ..schemas.support import BroadcastRequest, MessageCreate, MessageRead
from ..deps import CurrentPrincipal, DbSession, require

router = APIRouter(prefix="/messages", tags=["messages"])


def _visible_filters(principal: CurrentPrincipal):
    """
    A client sees their own thread; staff see the threads they are in.

    The two staff conditions are OR'd inside one element. Returning them as two
    elements would AND them at the caller's `.where(*filters)` and ask for
    messages a person both sent and received - which is none.
    """
    if principal.may_see_all_clients():
        return []
    if principal.client_id is not None:
        return [Message.client_id == principal.client_id]
    return [or_(Message.sender_id == principal.id, Message.recipient_id == principal.id)]


@router.get("", response_model=Page[MessageRead], summary="List messages",
            dependencies=[Depends(require("messages", "view"))])
def list_messages(
    db: DbSession,
    principal: CurrentPrincipal,
    thread_id: str | None = Query(None, max_length=80),
    unread_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[MessageRead]:
    stmt = select(Message)
    count_stmt = select(func.count()).select_from(Message)

    filters = []
    if thread_id:
        filters.append(Message.thread_id == thread_id)
    if unread_only:
        filters.append(Message.read_at.is_(None))
    filters.extend(_visible_filters(principal))

    if filters:
        stmt = stmt.where(*filters)
        count_stmt = count_stmt.where(*filters)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(stmt.order_by(Message.id).limit(limit).offset(offset)).all()
    return Page[MessageRead](
        items=[MessageRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.post("", response_model=MessageRead, status_code=status.HTTP_201_CREATED,
             summary="Send a message",
             dependencies=[Depends(require("messages", "send"))])
def send(payload: MessageCreate, db: DbSession, principal: CurrentPrincipal) -> MessageRead:
    """
    Send as yourself.

    Three things come from the token rather than the body: the sender, and the
    thread key, and - for a client - the client id. A coach who put somebody
    else's `client_id` in the body would otherwise be posting into that
    client's thread; their own client id is used instead and the body value is
    ignored. Only an account that may see every client can choose one.
    """
    client_id = principal.client_id
    if client_id is None and principal.may_see_all_clients():
        client_id = payload.client_id

    thread_id = payload.thread_id or (f"client:{client_id}" if client_id else f"account:{principal.id}")
    # A client must not be able to address a thread that is not theirs by
    # naming it in the body.
    if not principal.may_see_all_clients() and principal.client_id is not None:
        thread_id = f"client:{principal.client_id}"

    message = Message(
        thread_id=thread_id,
        sender_id=principal.id,
        recipient_id=payload.recipient_id,
        client_id=client_id,
        body=payload.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return MessageRead.model_validate(message)


@router.post("/broadcast", dependencies=[Depends(require("messages", "send"))])
def broadcast(payload: BroadcastRequest, db: DbSession, principal: CurrentPrincipal) -> Ok:
    """
    Fan a message out to every active account in the audience.

    The recipient set is computed in the server, never taken from the request:
    a broadcast that accepted a recipient list would be a mail relay.
    """
    if principal.tier > 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Broadcasting is admin or owner only",
        )

    stmt = select(Account).where(Account.is_active.is_(True))
    if payload.tiers:
        stmt = stmt.where(Account.tier.in_(payload.tiers))
    recipients = db.scalars(stmt).all()

    thread_id = f"broadcast:{payload.audience}"
    for account in recipients:
        db.add(
            Message(
                thread_id=thread_id,
                sender_id=principal.id,
                recipient_id=account.id,
                client_id=account.client_id,
                body=payload.body,
            )
        )
    db.commit()
    return Ok(detail=f"Sent to {len(recipients)} account(s)")


@router.post("/{message_id}/read", response_model=Ok, summary="Mark one message as read",
             dependencies=[Depends(require("messages", "view"))])
def mark_read(message_id: int, db: DbSession, principal: CurrentPrincipal) -> Ok:
    """
    Mark one message read, but only one the caller could have listed.

    The recipient check alone is not enough: a message with no recipient - the
    rows `POST /messages/broadcast` writes - would sail past it and let any
    reader mark any broadcast consumed on somebody else's behalf. So the row has
    to survive the same filter the list endpoint applies.
    """
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    reachable = int(
        db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.id == message_id, *_visible_filters(principal))
        )
        or 0
    )
    if reachable == 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your message")

    if message.read_at is None:
        message.read_at = datetime.now(timezone.utc)
        db.add(message)
        db.commit()
    return Ok(detail="Marked as read")


@router.post("/read-all", response_model=Ok, summary="Mark a whole thread as read",
             dependencies=[Depends(require("messages", "view"))])
def mark_thread_read(
    db: DbSession,
    principal: CurrentPrincipal,
    thread_id: str = Query(..., max_length=80),
) -> Ok:
    filters = [Message.thread_id == thread_id, Message.read_at.is_(None)]
    if not principal.may_see_all_clients():
        filters.append(
            or_(Message.recipient_id == principal.id, Message.client_id == principal.client_id)
        )
    rows = db.scalars(select(Message).where(*filters)).all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.read_at = now
        db.add(row)
    db.commit()
    return Ok(detail=f"Marked {len(rows)} message(s) as read")
