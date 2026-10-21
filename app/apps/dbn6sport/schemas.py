"""Pydantic schemas untuk dbn6sport. Field sama dengan frontend (tanpa translasi)."""
from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Any, Optional

from pydantic import BaseModel


# ---------- auth ----------
class LoginIn(BaseModel):
    login_id: str
    password: str = ""


class UserOut(BaseModel):
    id: str; name: str; role: str; login: str
    email: Optional[str] = None; wa: Optional[str] = None; loc: Optional[str] = None


# ---------- members ----------
class MemberIn(BaseModel):
    name: str; role: str; login: str
    email: Optional[str] = None; wa: Optional[str] = None; loc: Optional[str] = None
    password: Optional[str] = None


class MemberPatch(BaseModel):
    name: Optional[str] = None; role: Optional[str] = None
    email: Optional[str] = None; wa: Optional[str] = None; loc: Optional[str] = None


# ---------- programs ----------
class ProgramIn(BaseModel):
    name: str; price: int; unit: Optional[str] = None
    wk: int; lvl: float
    peserta: int = 1; fee: int = 0
    detail: Optional[dict] = None


class ProgramPatch(BaseModel):
    name: Optional[str] = None; price: Optional[int] = None
    unit: Optional[str] = None; wk: Optional[int] = None; lvl: Optional[float] = None
    peserta: Optional[int] = None; fee: Optional[int] = None
    detail: Optional[dict] = None


# ---------- clients ----------
class ClientIn(BaseModel):
    name: str; program_id: str; start: date_type
    coach_id: str
    cond: Optional[str] = "Prima"; renew: bool = False
    hrmax: Optional[int] = None; mp: Optional[int] = None
    note: Optional[str] = ""; grp: Optional[str] = None
    end: Optional[date_type] = None; end_orig: Optional[date_type] = None


class ClientPatch(BaseModel):
    name: Optional[str] = None; program_id: Optional[str] = None
    start: Optional[date_type] = None; end: Optional[date_type] = None
    end_orig: Optional[date_type] = None
    coach_id: Optional[str] = None; cond: Optional[str] = None
    renew: Optional[bool] = None; hrmax: Optional[int] = None
    mp: Optional[int] = None; note: Optional[str] = None
    grp: Optional[str] = None


# ---------- reports ----------
class ReportIn(BaseModel):
    date: date_type; type: Optional[str] = None
    plan_km: Optional[float] = None; km: Optional[float] = None
    pace: Optional[int] = None; hr: Optional[int] = None
    rasa: Optional[int] = None; note: Optional[str] = ""
    link_url: Optional[str] = None; missed: bool = False


class ReportPatch(BaseModel):
    type: Optional[str] = None; plan_km: Optional[float] = None
    km: Optional[float] = None; pace: Optional[int] = None
    hr: Optional[int] = None; rasa: Optional[int] = None
    note: Optional[str] = None; link_url: Optional[str] = None
    missed: Optional[bool] = None


class CorrectionIn(BaseModel):
    text: str


# ---------- bookings ----------
class BookingIn(BaseModel):
    coach_id: str; client_id: str; day: int; time: str


# ---------- requests ----------
class RequestIn(BaseModel):
    type: str; date: Optional[date_type] = None; date2: Optional[date_type] = None
    detail: Optional[str] = ""


class RequestPatch(BaseModel):
    status: Optional[str] = None


class TitipIn(BaseModel):
    client_id: str; date: date_type; from_coach: str; to_coach: str
    time: str; request_id: Optional[str] = None


# ---------- transactions ----------
class TransactionIn(BaseModel):
    date: date_type; type: str; category: str; amount: int
    desc: Optional[str] = ""; program_id: Optional[str] = None
    coach_id: Optional[str] = None


# ---------- messages ----------
class MessageIn(BaseModel):
    text: str


class BroadcastIn(BaseModel):
    to: str; text: str


# ---------- settings ----------
class SettingsPatch(BaseModel):
    targets: Optional[dict] = None; acl: Optional[dict] = None
    program_tpls: Optional[list] = None
    komisi: Optional[dict] = None  # Komisi Bulanan Fase B: {tgl_bayar: 'akhir'|1..28}


# ---------- activity ----------
class ActivityIn(BaseModel):
    text: str
