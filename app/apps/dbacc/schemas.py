"""Skema Pydantic — kontrak request/response (mirror js/api.js).

Salinan verbatim dari DB Acounting/backend/app/schemas.py (tidak diubah).
"""
from typing import Any, Dict, List

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AuthOut(BaseModel):
    token: str
    tier: int
    name: str
    email: str


class CompanyMeta(BaseModel):
    id: str
    name: str
    industry: str = ""
    color: str = "#1EB682"
    initial: str = ""


class CompanyCreate(BaseModel):
    name: str
    industry: str = ""
    color: str = "#1EB682"


class CompanyPayload(BaseModel):
    """Payload penuh perusahaan — struktur identik objek company frontend."""

    id: str
    name: str
    industry: str = ""
    color: str = "#1EB682"
    initial: str = ""
    npwp: str = ""
    fiscalStart: int = 1
    currency: str = "IDR"
    coa: List[Dict[str, Any]] = []
    journal: List[Dict[str, Any]] = []
    sales: List[Dict[str, Any]] = []
    purchases: List[Dict[str, Any]] = []
    cashbank: List[Dict[str, Any]] = []
    contacts: List[Dict[str, Any]] = []
    inventory: List[Dict[str, Any]] = []
    inventoryLogs: List[Dict[str, Any]] = []
    fixedAssets: List[Dict[str, Any]] = []
    counters: Dict[str, Any] = {}


class MetaSync(BaseModel):
    companies: List[CompanyMeta]


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=256)
