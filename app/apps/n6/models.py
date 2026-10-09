from __future__ import annotations
"""
ORM models.

One table group per menu of the dashboard, so the mapping between a sidebar
entry and a table stays obvious:

    Klien / Jadwal Klien   -> Client, ClientSchedule, Enrollment
    Jadwal Coach           -> Coach, CoachScheduleSlot, ScheduleRequest
    Harga & Program        -> Program, PriceItem
    Performa & Komisi      -> Commission
    Keuangan               -> Expense
    Tiket & Keluhan       -> Ticket, TicketReply
    Pesan                  -> Message
    Beranda (analytics)    -> read via /reports/monthly and /finance/summary
    Koreksi / Atlet        -> Correction, AthleteNote
    Client portal          -> the same rows, filtered by Account.client_id

Nothing here is required while the API is disabled; the frontend still reads
and writes localStorage. These tables are what the API reads once
API_ENABLED is turned on.
"""


from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import JSONType, app_base
Base = app_base("n6")

from .base import TimestampMixin

# --------------------------------------------------------------------- enums
# Kept as plain strings rather than a PG ENUM: adding a value then needs no
# migration, and the dashboard is small enough that the looseness is free.

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_HEADCOACH = "headcoach"
ROLE_COACH = "coach"
ROLE_CLIENT = "client"

CLIENT_ACTIVE = "aktif"
CLIENT_ARCHIVED = "arsip"

PROGRAM_DRAFT = "draft"
PROGRAM_PUBLISHED = "published"

TICKET_OPEN = "terbuka"
TICKET_REPLIED = "dibalas"
TICKET_CLOSED = "selesai"

REQUEST_PENDING = "menunggu"
REQUEST_APPROVED = "disetujui"
REQUEST_REJECTED = "ditolak"

CORRECTION_OPEN = "menunggu"
CORRECTION_RESOLVED = "selesai"

PAYMENT_UNPAID = "belum"
PAYMENT_PAID = "lunas"


# ------------------------------------------------------------------- accounts
class Account(Base, TimestampMixin):
    """A person who can sign in. `tier` is the number the access rule uses."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    #: 0 owner, 1 admin, 2 headcoach, 3 coach, 4 client. See core/tiers.py.
    #: Defaults to the most restricted tier so a half-filled signup cannot
    #: accidentally mint an owner.
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=4, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Tier-4 users belong to a client record; other tiers leave this null.
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="SET NULL"), index=True
    )
    #: Tier-3 users manage this coach's schedule and roster.
    coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.coaches.id", ondelete="SET NULL"), index=True
    )

    client: Mapped["Client | None"] = relationship(back_populates="accounts", foreign_keys=[client_id])
    coach: Mapped["Coach | None"] = relationship(back_populates="accounts", foreign_keys=[coach_id])

    __table_args__ = (
        Index("ix_accounts_tier_active", "tier", "is_active"),
        {"schema": "n6"},
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Account {self.username} tier={self.tier} active={self.is_active}>"


# --------------------------------------------------------------------- people
class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(16))
    birth_date: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CLIENT_ACTIVE, index=True)
    joined_on: Mapped[date] = mapped_column(Date, nullable=False)
    archived_on: Mapped[date | None] = mapped_column(Date)

    coach_id: Mapped[int | None] = mapped_column(ForeignKey("n6.coaches.id", ondelete="SET NULL"), index=True)

    coach: Mapped["Coach | None"] = relationship(back_populates="clients")
    accounts: Mapped[list["Account"]] = relationship(back_populates="client", foreign_keys="Account.client_id")
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )
    client_schedule: Mapped[list["ClientSchedule"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )

    __table_args__ = {"schema": "n6"}

    @property
    def is_archived(self) -> bool:
        return self.status == CLIENT_ARCHIVED


class Coach(Base, TimestampMixin):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CLIENT_ACTIVE, index=True)
    joined_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    #: Fraction of the client's fee paid to the coach, e.g. 0.40 for 40%.
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0.4000")
    )

    clients: Mapped[list["Client"]] = relationship(back_populates="coach")
    accounts: Mapped[list["Account"]] = relationship(back_populates="coach", foreign_keys="Account.coach_id")
    slots: Mapped[list["CoachScheduleSlot"]] = relationship(
        back_populates="coach", cascade="all, delete-orphan"
    )
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="coach")

    __table_args__ = {"schema": "n6"}


# -------------------------------------------------------------------- programs
class Program(Base, TimestampMixin):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(80), index=True)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    meeting_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PROGRAM_DRAFT, index=True)
    published_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    #: Free-form builder state the head coach saves. Shape owned by the UI.
    template: Mapped[dict | None] = mapped_column(JSONType)

    prices: Mapped[list["PriceItem"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="program")

    __table_args__ = (UniqueConstraint("name", "category", name="uq_programs_name_category"),
        {"schema": "n6"},
    )


class PriceItem(Base, TimestampMixin):
    """A line inside Harga & Program: one component of a program's price."""

    __tablename__ = "price_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.programs.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="per program")
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    #: Display order inside the program; null for standalone items.
    position: Mapped[int | None] = mapped_column(Integer)

    program: Mapped["Program | None"] = relationship(back_populates="prices")

    __table_args__ = {"schema": "n6"}


class Enrollment(Base, TimestampMixin):
    """One client's run of one program. Backs 'Pendaftaran' and revenue."""

    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.programs.id", ondelete="SET NULL"), index=True
    )
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("n6.coaches.id", ondelete="SET NULL"), index=True)

    start_on: Mapped[date] = mapped_column(Date, nullable=False)
    weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    price_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    payment_status: Mapped[str] = mapped_column(String(16), nullable=False, default=PAYMENT_UNPAID)
    paid_on: Mapped[date | None] = mapped_column(Date)
    custom_label: Mapped[str | None] = mapped_column(String(160))

    client: Mapped["Client"] = relationship(back_populates="enrollments")
    program: Mapped["Program | None"] = relationship(back_populates="enrollments")
    coach: Mapped["Coach | None"] = relationship()

    @property
    def end_on(self) -> date:
        return self.start_on + _weeks(self.weeks)


def _weeks(weeks: int):
    from datetime import timedelta

    return timedelta(weeks=max(0, int(weeks or 0)))

    __table_args__ = {"schema": "n6"}


# ------------------------------------------------------------------- schedules
class CoachScheduleSlot(Base, TimestampMixin):
    """One recurring availability block in the coach's weekly template."""

    __tablename__ = "coach_schedule_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        ForeignKey("n6.coaches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: 1 = Monday .. 7 = Sunday, matching the dashboard's day tabs.
    weekday: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    location: Mapped[str | None] = mapped_column(String(160))
    training_category: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    coach: Mapped["Coach"] = relationship(back_populates="slots")

    __table_args__ = (
        UniqueConstraint("coach_id", "weekday", "start_time", name="uq_slots_coach_weekday_start"),
        {"schema": "n6"},
    )


class ClientSchedule(Base, TimestampMixin):
    """One recurring block in an individual client's weekly plan."""

    __tablename__ = "client_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str | None] = mapped_column(String(5))
    location: Mapped[str | None] = mapped_column(String(160))
    training_category: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    client: Mapped["Client"] = relationship(back_populates="client_schedule")

    __table_args__ = (
        UniqueConstraint("client_id", "weekday", "start_time", name="uq_csched_client_weekday_start"),
        {"schema": "n6"},
    )


class ScheduleRequest(Base, TimestampMixin):
    """A client's ask to move a session. Resolved by admin/head coach."""

    __tablename__ = "schedule_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coach_id: Mapped[int | None] = mapped_column(ForeignKey("n6.coaches.id", ondelete="SET NULL"), index=True)
    requested_on: Mapped[date] = mapped_column(Date, nullable=False)
    current_start: Mapped[str | None] = mapped_column(String(5))
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=REQUEST_PENDING, index=True)
    decision_note: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped["Client"] = relationship()

    __table_args__ = {"schema": "n6"}


# --------------------------------------------------------------------- finance
class Expense(Base, TimestampMixin):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))

    __table_args__ = {"schema": "n6"}


class Commission(Base, TimestampMixin):
    """A coach's earnings for one month. Owner/Performa & Komisi."""

    __tablename__ = "commissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        ForeignKey("n6.coaches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    paid_on: Mapped[date | None] = mapped_column(Date)

    coach: Mapped["Coach"] = relationship()

    __table_args__ = (
        UniqueConstraint("coach_id", "period", name="uq_commissions_coach_period"),
        {"schema": "n6"},
    )


# ------------------------------------------------------- support: tickets, chat
class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="sedang", index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=TICKET_OPEN, index=True)
    opened_by: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client: Mapped["Client | None"] = relationship()
    replies: Mapped[list["TicketReply"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketReply.created_at"
    )

    __table_args__ = {"schema": "n6"}


class TicketReply(Base, TimestampMixin):
    __tablename__ = "ticket_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("n6.tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="replies")

    __table_args__ = {"schema": "n6"}


class Message(Base, TimestampMixin):
    """One chat message. `thread_id` groups a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"), index=True)
    recipient_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.accounts.id", ondelete="SET NULL"), index=True
    )
    client_id: Mapped[int | None] = mapped_column(ForeignKey("n6.clients.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    #: Set by POST /messages/{id}/read; drives the unread dots in the sidebar.
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sender: Mapped["Account | None"] = relationship(foreign_keys=[sender_id])
    recipient: Mapped["Account | None"] = relationship(foreign_keys=[recipient_id])
    client: Mapped["Client | None"] = relationship()

    __table_args__ = {"schema": "n6"}


class Attendance(Base, TimestampMixin):
    """One client's presence on one day, per coach. Backs Absensi."""

    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coach_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.coaches.id", ondelete="SET NULL"), index=True
    )
    session_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="hadir")
    note: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))

    client: Mapped["Client"] = relationship()
    coach: Mapped["Coach | None"] = relationship(back_populates="attendances")

    __table_args__ = (
        UniqueConstraint("client_id", "session_on", name="uq_attendance_client_day"),
        {"schema": "n6"},
    )


# ------------------------------------------------------------- head coach tools
class Correction(Base, TimestampMixin):
    """A client's proposed change to their own record. Koreksi."""

    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text)
    after_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CORRECTION_OPEN, index=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = {"schema": "n6"}


class AthleteNote(Base, TimestampMixin):
    """Head coach's private tracking for one client. Atlet Binaan."""

    __tablename__ = "athlete_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period: Mapped[str | None] = mapped_column(String(7))  # YYYY-MM
    pace_target: Mapped[str | None] = mapped_column(String(32))
    hr_target: Mapped[int | None] = mapped_column(Integer)
    intensity: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    #: Tri-state flags surfaced by GET /monitoring/flags
    flag_kehadiran: Mapped[str | None] = mapped_column(String(16))
    flag_ordinal: Mapped[str | None] = mapped_column(String(32))
    flag_komisi: Mapped[str | None] = mapped_column(String(16))

    client: Mapped["Client"] = relationship()

    __table_args__ = (
        UniqueConstraint("client_id", "period", name="uq_athlete_client_period"),
        {"schema": "n6"},
    )


class MonthlyReport(Base, TimestampMixin):
    """A generated month-end PDF/JSON payload. Laporan bulanan."""

    __tablename__ = "monthly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    scope: Mapped[str] = mapped_column(String(32), nullable=False, default="all")
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="owner")
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("n6.accounts.id", ondelete="SET NULL"))
    #: Figures at generation time. Kept verbatim so a re-run never rewrites
    #: what was already handed to somebody.
    payload: Mapped[dict | None] = mapped_column(JSONType)

    __table_args__ = (
        UniqueConstraint("period", "scope", "audience", name="uq_reports_period_scope_audience"),
        {"schema": "n6"},
    )


class TrainingLog(Base, TimestampMixin):
    """A client's workout log entry. Dikirim client, dibaca coach/head coach."""

    __tablename__ = "training_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("n6.clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    client: Mapped["Client"] = relationship()

    __table_args__ = {"schema": "n6"}


__all__ = [
    "Base",
    "Account",
    "Client",
    "Coach",
    "Program",
    "PriceItem",
    "Enrollment",
    "CoachScheduleSlot",
    "ClientSchedule",
    "ScheduleRequest",
    "Expense",
    "Commission",
    "Ticket",
    "TicketReply",
    "Message",
    "Attendance",
    "Correction",
    "AthleteNote",
    "MonthlyReport",
    "TrainingLog",
    "ROLE_OWNER",
    "ROLE_ADMIN",
    "ROLE_HEADCOACH",
    "ROLE_COACH",
    "ROLE_CLIENT",
    "CLIENT_ACTIVE",
    "CLIENT_ARCHIVED",
    "PROGRAM_DRAFT",
    "PROGRAM_PUBLISHED",
    "TICKET_OPEN",
    "TICKET_REPLIED",
    "TICKET_CLOSED",
    "REQUEST_PENDING",
    "REQUEST_APPROVED",
    "REQUEST_REJECTED",
    "CORRECTION_OPEN",
    "CORRECTION_RESOLVED",
    "PAYMENT_UNPAID",
    "PAYMENT_PAID",
]