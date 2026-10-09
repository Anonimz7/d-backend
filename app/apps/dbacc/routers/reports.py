"""Laporan agregat dihitung server dari payload (oportunitas pindah ke SQL
relasional di fase 2). Rumus laba/rugi & saldo mengikuti frontend agar
angka konsisten: normal debit = Aset/Beban, normal kredit = sisanya.

Salinan dari DB Acounting/backend/app/routers/reports.py — hanya import
yang diadaptasi (access, get_db dari core). Logika & kontrak tidak berubah.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import require_menu

router = APIRouter(prefix="/companies/{company_id}/reports", tags=["reports"])


def _payload(db: Session, company_id: str) -> dict:
    c = db.query(models.Company).filter(models.Company.id == company_id).first()
    return (c.payload if c else {}) or {}


def _sums(payload: dict, from_date=None, to_date=None) -> dict:
    coa = {a.get("code"): a for a in payload.get("coa", [])}
    rev = exp = 0.0
    for j in payload.get("journal", []):
        if from_date and j.get("date", "") < from_date:
            continue
        if to_date and j.get("date", "") > to_date:
            continue
        for line in j.get("lines", []):
            acc = coa.get(line.get("account"))
            if not acc:
                continue
            if acc.get("type") == "Pendapatan":
                rev += (line.get("credit") or 0) - (line.get("debit") or 0)
            elif acc.get("type") == "Beban":
                exp += (line.get("debit") or 0) - (line.get("credit") or 0)
    return {"rev": rev, "exp": exp, "profit": rev - exp}


@router.get("/labarugi")
def labarugi(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("laporan"))):
    return _sums(_payload(db, company_id))


@router.get("/neraca")
def neraca(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("laporan"))):
    payload = _payload(db, company_id)
    coa = {a.get("code"): a for a in payload.get("coa", [])}
    bal: dict[str, float] = {}
    for j in payload.get("journal", []):
        for line in j.get("lines", []):
            acc = coa.get(line.get("account"))
            if not acc:
                continue
            normal_debit = acc.get("type") in ("Aset", "Beban")
            delta = (line.get("debit") or 0) - (line.get("credit") or 0)
            bal[line["account"]] = bal.get(line["account"], 0.0) + (delta if normal_debit else -delta)
    return {"balances": bal, "sums": _sums(payload)}


@router.get("/pajak")
def pajak(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("pajak"))):
    payload = _payload(db, company_id)
    keluaran = sum(s.get("tax", 0) for s in payload.get("sales", []))
    masukan = sum(p.get("tax", 0) for p in payload.get("purchases", []))
    return {"keluaran": keluaran, "masukan": masukan, "net": keluaran - masukan}
