from __future__ import annotations
"""Programs and the price list (menu: Harga & Program)."""


from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from .common import ORMModel


class PriceItemIn(BaseModel):
    #: Set when the row already exists. PUT /pricing uses it to edit in place;
    #: POST /programs rejects it, so creating always means creating.
    id: int | None = None
    label: str = Field(min_length=1, max_length=160)
    unit: str = Field(default="per program", max_length=32)
    price: Decimal = Field(default=Decimal("0"), ge=0)
    position: int | None = None


class PriceItemRead(ORMModel):
    id: int
    program_id: int | None = None
    label: str
    unit: str
    price: Decimal
    position: int | None = None


class ProgramCreate(BaseModel):
    #: See PriceItemIn.id. PUT /pricing carries it so a re-save updates the
    #: program in place instead of replacing it, which is what keeps the
    #: enrolments that point at it.
    id: int | None = None
    name: str = Field(min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    duration_weeks: int = Field(default=4, ge=1, le=104)
    meeting_per_week: int = Field(default=3, ge=1, le=14)
    price: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str | None = None
    #: Free-form builder state; the UI owns the shape.
    template: dict[str, Any] | None = None
    prices: list[PriceItemIn] = Field(default_factory=list)


class ProgramPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    duration_weeks: int | None = Field(default=None, ge=1, le=104)
    meeting_per_week: int | None = Field(default=None, ge=1, le=14)
    price: Decimal | None = Field(default=None, ge=0)
    notes: str | None = None
    template: dict[str, Any] | None = None
    prices: list[PriceItemIn] | None = None


class ProgramRead(ORMModel):
    id: int
    name: str
    category: str | None = None
    duration_weeks: int
    meeting_per_week: int
    price: Decimal
    status: str
    published_on: date | None = None
    notes: str | None = None
    template: dict[str, Any] | None = None
    created_at: datetime | None = None
    prices: list[PriceItemRead] = Field(default_factory=list)


class PricingRead(BaseModel):
    """GET /pricing - the whole Harga & Program screen in one payload."""

    programs: list[ProgramRead] = Field(default_factory=list)
    standalone: list[PriceItemRead] = Field(default_factory=list)
    updated_at: datetime | None = None


class PricingWrite(BaseModel):
    """
    PUT /pricing - the whole catalogue in one body, matching how the screen saves.

    Diff-based, not replace-based: rows carrying an `id` are updated, rows
    without one are inserted, and a row that is in the database but not in this
    body is deleted - unless something is still enrolled in it, which is a 409
    rather than a silently broken client record.
    """

    programs: list[ProgramCreate] = Field(default_factory=list)
    standalone: list[PriceItemIn] = Field(default_factory=list)