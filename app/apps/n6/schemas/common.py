from __future__ import annotations
"""Shapes shared by more than one resource."""


from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")

PERIOD_RE = r"^\d{4}-\d{2}$"


class ORMModel(BaseModel):
    """Reads straight from an ORM row."""

    model_config = ConfigDict(from_attributes=True)


class Ok(BaseModel):
    """Uniform acknowledgement. ``detail`` is safe to show a user."""

    ok: bool = True
    detail: str = ""


class Page(BaseModel, Generic[T]):
    """Envelope for every list endpoint, so the client never guesses."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0

    @property
    def has_more(self) -> bool:  # pragma: no cover - convenience
        return self.offset + len(self.items) < self.total


class Period(BaseModel):
    """A YYYY-MM window, the shape every finance screen asks for."""

    period: str | None = Field(default=None, pattern=PERIOD_RE)

    @field_validator("period")
    @classmethod
    def _default_to_current_month(cls, v: str | None) -> str | None:
        return v or date.today().strftime("%Y-%m")


class PeriodOut(BaseModel):
    period: str
    from_date: date
    to_date: date


class CountByCategory(BaseModel):
    """One row of a chart or breakdown list."""

    key: str
    label: str = ""
    count: int = 0
    amount: float = 0.0