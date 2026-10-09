"""Bentuk data yang diterima dan dikirim API. Nama field = dokumen yang dipakai services/mappers.js."""
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Id = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")]
Color = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]
Icon = Annotated[str, Field(min_length=1, max_length=20)]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Profile(Schema):
    name: str = Field(min_length=1, max_length=120)
    theme: Literal["dark", "light", "system"]
    hide_balance: bool


class Account(Schema):
    id: Id
    name: str = Field(min_length=1, max_length=30)
    type: Literal["bank", "ewallet", "tunai", "lain"]
    number: str = Field(default="", max_length=24)
    color: Color
    opening_balance: int


class Transaction(Schema):
    id: Id
    ts: int
    type: Literal["in", "out", "tf"]
    category: str | None = Field(default=None, max_length=30)
    amount: int = Field(gt=0)
    date: date
    description: str = Field(default="", max_length=500)
    account_id: str | None = None
    from_account_id: str | None = None
    to_account_id: str | None = None

    @model_validator(mode="after")
    def check_by_type(self):
        if self.type == "tf":
            if not (self.from_account_id and self.to_account_id):
                raise ValueError("Transfer membutuhkan from_account_id dan to_account_id")
            if self.from_account_id == self.to_account_id:
                raise ValueError("Rekening asal dan tujuan harus berbeda")
        elif not (self.account_id and self.category):
            raise ValueError("Pemasukan/pengeluaran membutuhkan account_id dan category")
        return self


class Budget(Schema):
    category: str = Field(min_length=1, max_length=30)
    limit: int = Field(ge=0)


class Bill(Schema):
    id: Id
    name: str = Field(min_length=1, max_length=120)
    amount: int = Field(gt=0)
    due_date: date
    icon: Icon
    color: Color


class Goal(Schema):
    id: Id
    name: str = Field(min_length=1, max_length=120)
    saved: int = Field(ge=0)
    target: int = Field(gt=0)
    icon: Icon
    color: Color


class Investment(Schema):
    id: Id
    name: str = Field(min_length=1, max_length=120)
    value: int = Field(gt=0)
    return_pct: float
    icon: Icon
    color: Color


class State(Schema):
    """Dokumen lengkap. Bagian yang tidak boleh diakses tier pengguna tidak dikirim (None)."""

    profile: Profile | None = None
    accounts: list[Account] | None = None
    transactions: list[Transaction] | None = None
    budgets: list[Budget] | None = None
    bills: list[Bill] | None = None
    goals: list[Goal] | None = None
    investments: list[Investment] | None = None


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    tier: int


class AccessOut(BaseModel):
    tier: int
    name: str
    access: list[str]
