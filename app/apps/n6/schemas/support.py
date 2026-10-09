from __future__ import annotations
"""Tickets, chat, attendance and corrections."""


from datetime import date, datetime

from pydantic import BaseModel, Field

from .common import ORMModel


# ------------------------------------------------------------------- tickets
class TicketRead(ORMModel):
    """A ticket as the list renders it. `reply_count`/`last_reply_at` are
    computed by the endpoint from the replies collection, not stored."""

    id: int
    client_id: int | None = None
    subject: str
    detail: str | None = None
    priority: str
    status: str
    opened_by: int | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    reply_count: int = 0
    last_reply_at: datetime | None = None


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1)


class TicketClose(BaseModel):
    note: str | None = Field(default=None, max_length=1000)
    resolution: str | None = Field(default=None, max_length=64)


# ------------------------------------------------------------------ messages
class MessageCreate(BaseModel):
    """POST /messages. The thread key is derived server-side, never trusted from
    the body, so one account cannot post into another's conversation."""

    body: str = Field(min_length=1)
    thread_id: str | None = Field(default=None, max_length=80)
    recipient_id: int | None = None
    client_id: int | None = None


class MessageRead(ORMModel):
    id: int
    thread_id: str
    sender_id: int | None = None
    recipient_id: int | None = None
    client_id: int | None = None
    body: str
    read_at: datetime | None = None
    created_at: datetime | None = None


class BroadcastRequest(BaseModel):
    body: str = Field(min_length=1)
    #: Restrict to these tiers. Omit to reach every active account.
    tiers: list[int] | None = None
    audience: str = Field(default="all", max_length=32)


# ---------------------------------------------------------------- attendance
class AttendanceCreate(BaseModel):
    client_id: int
    coach_id: int | None = None
    session_on: date = Field(default_factory=date.today)
    status: str = Field(default="hadir", pattern=r"^(hadir|izin|sakit|alpha)$")
    note: str | None = None


class AttendanceRead(ORMModel):
    id: int
    client_id: int
    coach_id: int | None = None
    session_on: date
    status: str
    note: str | None = None
    created_at: datetime | None = None


# --------------------------------------------------------------- corrections
class CorrectionCreate(BaseModel):
    client_id: int | None = None
    field: str = Field(min_length=1, max_length=64)
    after_value: str | None = None
    reason: str | None = None


class CorrectionRead(ORMModel):
    id: int
    client_id: int | None = None
    field: str
    before_value: str | None = None
    after_value: str | None = None
    reason: str | None = None
    status: str
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None


class CorrectionResolve(BaseModel):
    resolution_note: str | None = Field(default=None, max_length=1000)
    #: Also write the proposed value onto the client record.
    apply_to_client: bool = True


# ------------------------------------------------------------------ athletes
class AthleteUpdate(BaseModel):
    """PUT /athletes/{id} - the client_id is in the path, so is the row."""

    period: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")
    pace_target: str | None = Field(default=None, max_length=32)
    hr_target: int | None = Field(default=None, ge=0, le=260)
    intensity: int | None = Field(default=None, ge=1, le=10)
    note: str | None = None
    flag_kehadiran: str | None = Field(default=None, max_length=16)
    flag_ordinal: str | None = Field(default=None, max_length=32)
    flag_komisi: str | None = Field(default=None, max_length=16)


class AthleteRead(ORMModel):
    """
    One roster row. `id` is the AthleteNote row id, or 0 when the head coach
    has not written this client's targets yet - a client with no note is still
    on the roster, so the row is built from Client, not from AthleteNote.
    """

    id: int
    client_id: int
    client_name: str | None = None
    period: str | None = None
    pace_target: str | None = None
    hr_target: int | None = None
    intensity: int | None = None
    note: str | None = None
    flag_kehadiran: str | None = None
    flag_ordinal: str | None = None
    flag_komisi: str | None = None
    #: The month's attendance, counted by GET /monitoring/clients. Derived,
    #: so these three are not stored.
    present: int = 0
    sessions: int = 0
    rate: float = 0.0