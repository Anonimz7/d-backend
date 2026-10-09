from __future__ import annotations
"""Clients and enrolments (menu: Klien)."""


from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from .common import ORMModel


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    gender: str | None = Field(default=None, max_length=16)
    birth_date: date | None = None
    address: str | None = None
    notes: str | None = None
    joined_on: date = Field(default_factory=date.today)
    coach_id: int | None = None
    #: Optional first enrolment, created together with the client.
    program_id: int | None = None
    weeks: int | None = Field(default=None, ge=1, le=104)
    price_paid: Decimal | None = Field(default=None, ge=0)


class ClientPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    gender: str | None = Field(default=None, max_length=16)
    birth_date: date | None = None
    address: str | None = None
    notes: str | None = None
    coach_id: int | None = None


class ArchiveRequest(BaseModel):
    """POST /clients/{id}/archive"""

    archived_on: date = Field(default_factory=date.today)
    reason: str | None = Field(default=None, max_length=500)
    #: Archive or restore. Restoring is the same call with false.
    archived: bool = True

    @model_validator(mode="after")
    def _reason_when_archiving(self) -> "ArchiveRequest":
        if self.archived and not self.reason:
            # The dashboard always offers the reason box; keep that contract.
            self.reason = "diarsipkan dari dashboard"
        return self


class ClientRead(ORMModel):
    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    address: str | None = None
    notes: str | None = None
    status: str
    joined_on: date
    archived_on: date | None = None
    coach_id: int | None = None
    created_at: datetime | None = None


class ClientDetail(ClientRead):
    """GET /clients/{id} adds the roster view used by the detail modal."""

    coach_name: str | None = None
    active_enrollments: list["EnrollmentRead"] = Field(default_factory=list)
    schedule: list["ClientScheduleLite"] = Field(default_factory=list)


class ClientScheduleLite(BaseModel):
    weekday: int
    start_time: str
    end_time: str | None = None
    location: str | None = None
    training_category: str | None = None


class EnrollmentCreate(BaseModel):
    program_id: int | None = None
    coach_id: int | None = None
    start_on: date = Field(default_factory=date.today)
    weeks: int = Field(default=4, ge=1, le=104)
    price_paid: Decimal = Field(default=Decimal("0"), ge=0)
    payment_status: str = Field(default="belum", max_length=16)
    custom_label: str | None = Field(default=None, max_length=160)


class EnrollmentRead(ORMModel):
    id: int
    client_id: int
    program_id: int | None = None
    coach_id: int | None = None
    start_on: date
    weeks: int
    price_paid: Decimal
    payment_status: str
    paid_on: date | None = None
    custom_label: str | None = None


ClientDetail.model_rebuild()