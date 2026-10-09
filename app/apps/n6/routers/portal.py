from __future__ import annotations
"""
/portal - the client-facing view.

This is the only router a tier-4 client can reach, and the tier file lists
exactly these routes under ``endpoints.allow``. Everything here resolves from
``Account.client_id``, taken from the token and never from the query string, so
a client cannot reach another client's figures by editing a URL.

Writes are deliberately narrow: contact details and messages. Money, schedules
and staff records are not routed here at all, rather than being routed and
answering 403 - a 404 tells the caller nothing is possible, a 403 tells them to
look for a way round.
"""

"""Porting dari N6/backend/app/api/v1/endpoints/portal.py.

Import diadaptasi ke unified-backend; handler tidak diubah.
Lihat PORTING.md.
"""


from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from ..period import current_month
from ..models import Message, MonthlyReport, TrainingLog
from ..schemas.account import AccountPatch, AccountRead
from ..schemas.common import Ok, ORMModel, Page
from ..schemas.report import ClientSummary, MonthlyReportRead, ReportSummary
from ..schemas.support import MessageCreate, MessageRead
from .reports import build_report, client_summary
from ..deps import CurrentPrincipal, DbSession

router = APIRouter(prefix="/portal", tags=["portal"])

#: Contact fields a client may change about themselves.
SELF_EDITABLE = ("full_name", "email", "phone")

#: Report audiences a client is shown.
MY_AUDIENCES = ("client", "all")


def _require_linked(principal: CurrentPrincipal) -> int:
    client_id = principal.client_id
    if client_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account is not linked to a client record",
        )
    return client_id


def _my_thread(principal: CurrentPrincipal) -> str:
    """The one thread key a client may read and write."""
    return f"client:{_require_linked(principal)}"


@router.get("/me", response_model=AccountRead, summary="My account")
def me(principal: CurrentPrincipal) -> AccountRead:
    return AccountRead.model_validate(principal.account)


@router.patch("/me", response_model=AccountRead, summary="Change my contact details")
def update_me(
    payload: AccountPatch, db: DbSession, principal: CurrentPrincipal
) -> AccountRead:
    """
    Self-service edit of name, email and phone, and nothing else.

    `AccountPatch` also carries `is_active`, `client_id` and `coach_id`. Those
    are dropped here rather than honoured: a client must not be able to
    deactivate themselves out of the tier file's expectations, nor re-link
    their account to a different client or onto a coach's roster.
    """
    body = payload.model_dump(exclude_unset=True)
    account = principal.account
    for field in SELF_EDITABLE:
        if field in body:
            setattr(account, field, body[field])

    db.add(account)
    db.commit()
    db.refresh(account)
    return AccountRead.model_validate(account)


@router.get("/me/summary", response_model=ClientSummary, summary="My own card")
def my_card(db: DbSession, principal: CurrentPrincipal) -> ClientSummary:
    """The card from /reports/clients/{id}/summary, resolved to me."""
    return client_summary(_require_linked(principal), db, principal, current_month())


@router.get("/reports", response_model=Page[MonthlyReportRead],
            summary="Reports shared with my audience")
def my_reports(db: DbSession, principal: CurrentPrincipal) -> Page[MonthlyReportRead]:
    """
    Documents the gym generated for this audience.

    Filtered by audience rather than by client_id: a report is a document, and
    the question is which documents this role is allowed to see, which is what
    `audience` records.
    """
    rows = db.scalars(
        select(MonthlyReport)
        .where(MonthlyReport.audience.in_(MY_AUDIENCES))
        .order_by(MonthlyReport.period.desc())
    ).all()
    return Page[MonthlyReportRead](
        items=[MonthlyReportRead.model_validate(r) for r in rows],
        total=len(rows),
        limit=len(rows) or 1,
        offset=0,
    )


@router.get("/reports/summary", response_model=ReportSummary,
            summary="This month's figures")
def my_summary(db: DbSession, principal: CurrentPrincipal) -> ReportSummary:
    """
    The gym-wide month, computed live.

    A client sees aggregates - the same figures the Beranda screen shows - not
    their coach's revenue line. That difference is the whole reason this exists
    next to /reports/monthly, which is gated on `reports.view` and is absent
    from the client tier file.
    """
    return build_report(db, current_month())


@router.get("/messages", response_model=Page[MessageRead], summary="My messages")
def my_messages(
    db: DbSession,
    principal: CurrentPrincipal,
    unread_only: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[MessageRead]:
    """
    My thread with the gym.

    Scoped by client_id *and* by the `client:{id}` thread key: either alone
    would be enough for the dashboard, but the thread key is what makes the
    unread badge count the same rows this returns.
    """
    client_id = _require_linked(principal)
    filters = [
        Message.client_id == client_id,
        Message.thread_id == _my_thread(principal),
    ]
    if unread_only:
        filters.append(Message.read_at.is_(None))

    total = int(db.scalar(select(func.count()).select_from(Message).where(*filters)) or 0)
    rows = db.scalars(
        select(Message).where(*filters).order_by(Message.id).limit(limit).offset(offset)
    ).all()
    return Page[MessageRead](
        items=[MessageRead.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/messages", response_model=MessageRead,
             status_code=status.HTTP_201_CREATED, summary="Send the gym a message")
def send_message(
    payload: MessageCreate, db: DbSession, principal: CurrentPrincipal
) -> MessageRead:
    """
    Post into my own thread.

    Both the thread key and the sender are derived here. A body carrying a
    different `thread_id` is ignored, so this cannot be used to post into
    somebody else's conversation.
    """
    client_id = _require_linked(principal)
    message = Message(
        thread_id=f"client:{client_id}",
        sender_id=principal.id,
        client_id=client_id,
        body=payload.body,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return MessageRead.model_validate(message)


@router.post("/messages/read", response_model=Ok, summary="Mark my thread as read")
def read_messages(db: DbSession, principal: CurrentPrincipal) -> Ok:
    filters = [Message.thread_id == _my_thread(principal), Message.read_at.is_(None)]
    rows = db.scalars(select(Message).where(*filters)).all()
    now = datetime.now(timezone.utc)
    for row in rows:
        row.read_at = now
        db.add(row)
    db.commit()
    return Ok(detail=f"Marked {len(rows)} message(s) as read")


@router.get("/unread", response_model=dict, summary="Badge counter for the sidebar")
def unread(db: DbSession, principal: CurrentPrincipal) -> dict:
    """
    Count of messages from the gym I have not opened.

    Excludes my own messages: a thread where I have just written still shows as
    read, which is what a user expects and what a naive count gets wrong.
    """
    client_id = _require_linked(principal)
    count = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.client_id == client_id,
            Message.thread_id == f"client:{client_id}",
            Message.read_at.is_(None),
            Message.sender_id.is_not(principal.id),
        )
    )
    return {"unread": int(count or 0)}

# ------------------------------------------------------- training logs
class TrainingLogCreate(BaseModel):
    log_date: date
    content: str = Field(min_length=1, max_length=5000)


class TrainingLogRead(ORMModel):
    id: int
    client_id: int
    log_date: date
    content: str
    created_at: datetime | None = None


@router.post("/training-logs", response_model=TrainingLogRead,
             summary="Submit a training log (client)")
def submit_training_log(payload: TrainingLogCreate, db: DbSession,
                        principal: CurrentPrincipal) -> TrainingLogRead:
    client_id = _require_linked(principal)
    row = TrainingLog(
        client_id=client_id,
        log_date=payload.log_date,
        content=payload.content.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TrainingLogRead.model_validate(row)


@router.get("/training-logs", response_model=Page[TrainingLogRead],
            summary="My training logs (client)")
def my_training_logs(db: DbSession, principal: CurrentPrincipal,
                     limit: int = Query(50, ge=1, le=200),
                     offset: int = Query(0, ge=0)) -> Page[TrainingLogRead]:
    client_id = _require_linked(principal)
    base = select(TrainingLog).where(TrainingLog.client_id == client_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(TrainingLog.log_date.desc(), TrainingLog.id.desc())
        .limit(limit).offset(offset)
    ).all()
    return Page[TrainingLogRead](
        items=[TrainingLogRead.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )
