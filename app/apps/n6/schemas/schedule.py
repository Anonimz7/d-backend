from __future__ import annotations
"""Schedules and change requests (menus: Jadwal Coach, Jadwal Klien)."""


from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from .common import ORMModel


class SlotIn(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    #: Optional: a client's plan may record only a start time, while a coach
    #: availability block always has one.
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    location: str | None = Field(default=None, max_length=160)
    training_category: str | None = Field(default=None, max_length=80)
    note: str | None = None
    active: bool = True

    @field_validator("end_time")
    @classmethod
    def _ends_after_it_starts(cls, v: str | None, info) -> str | None:
        start = info.data.get("start_time")
        if v and start and v <= start:
            raise ValueError("end_time must be later than start_time")
        return v


class CoachScheduleWrite(BaseModel):
    """PUT /schedules/coach - full replace of one coach's weekly template."""

    coach_id: int
    slots: list[SlotIn] = Field(default_factory=list)


class CoachScheduleRead(BaseModel):
    coach_id: int
    coach_name: str | None = None
    slots: list[SlotIn] = Field(default_factory=list)


class ClientScheduleWrite(BaseModel):
    """PUT /schedules/clients/{client_id} - full replace of one client's plan."""

    slots: list[SlotIn] = Field(default_factory=list)


class ClientScheduleRead(BaseModel):
    client_id: int
    client_name: str | None = None
    slots: list[SlotIn] = Field(default_factory=list)


class RequestDecision(BaseModel):
    """PUT /schedules/coach/requests/{id}"""

    status: str = Field(pattern=r"^(disetujui|ditolak)$")
    decision_note: str | None = Field(default=None, max_length=1000)
    #: When approving, optionally move the session to this slot instead.
    new_start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    new_weekday: int | None = Field(default=None, ge=1, le=7)


class ScheduleRequestRead(ORMModel):
    id: int
    client_id: int | None = None
    coach_id: int | None = None
    requested_on: date
    current_start: str | None = None
    reason: str | None = None
    status: str
    decision_note: str | None = None
    decided_at: datetime | None = None
    created_at: datetime | None = None