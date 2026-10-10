"""Laporan agregat via SQL relasional (migrasi dari JSON payload).

Rumus laba/rugi & saldo mengikuti logika sebelumnya:
normal debit = Aset/Beban, normal kredit = sisanya.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import require_menu

router = APIRouter(prefix="/companies/{company_id}/reports", tags=["reports"])


def _sums(db: Session, company_id: str, from_date=None, to_date=None) -> dict:
    q = db.query(
        models.CoaAccount.type,
        func.sum(models.JournalLine.credit - models.JournalLine.debit).label("net_credit"),
        func.sum(models.JournalLine.debit - models.JournalLine.credit).label("net_debit"),
    ).join(
        models.JournalLine, models.JournalLine.account_id == models.CoaAccount.id
    ).join(
        models.Journal, models.JournalLine.journal_id == models.Journal.id
    ).filter(
        models.CoaAccount.company_id == company_id,
        models.Journal.company_id == company_id,
    )
    if from_date:
        q = q.filter(models.Journal.date >= from_date)
    if to_date:
        q = q.filter(models.Journal.date <= to_date)
    q = q.group_by(models.CoaAccount.type)

    rev = exp = 0.0
    for acc_type, net_credit, net_debit in q.all():
        if acc_type == "Pendapatan":
            rev += float(net_credit or 0)
        elif acc_type == "Beban":
            exp += float(net_debit or 0)
    return {"rev": rev, "exp": exp, "profit": rev - exp}


@router.get("/labarugi")
def labarugi(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("laporan"))):
    return _sums(db, company_id)


@router.get("/neraca")
def neraca(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("laporan"))):
    rows = db.query(
        models.CoaAccount.code,
        models.CoaAccount.name,
        models.CoaAccount.type,
        func.sum(models.JournalLine.debit - models.JournalLine.credit).label("net_debit"),
    ).join(
        models.JournalLine, models.JournalLine.account_id == models.CoaAccount.id
    ).join(
        models.Journal, models.JournalLine.journal_id == models.Journal.id
    ).filter(
        models.CoaAccount.company_id == company_id,
        models.Journal.company_id == company_id,
    ).group_by(
        models.CoaAccount.code, models.CoaAccount.name, models.CoaAccount.type
    ).all()

    bal: dict[str, float] = {}
    for code, name, acc_type, net_debit in rows:
        normal_debit = acc_type in ("Aset", "Beban")
        delta = float(net_debit or 0)
        bal[code] = delta if normal_debit else -delta
    return {"balances": bal, "sums": _sums(db, company_id)}


@router.get("/pajak")
def pajak(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("pajak"))):
    # Pajak dihitung dari total faktur; kolom tax ditambahkan bila tersedia
    keluaran = db.query(func.sum(models.SalesInvoice.total)).filter(
        models.SalesInvoice.company_id == company_id
    ).scalar() or 0
    masukan = db.query(func.sum(models.PurchaseInvoice.total)).filter(
        models.PurchaseInvoice.company_id == company_id
    ).scalar() or 0
    keluaran, masukan = float(keluaran), float(masukan)
    return {"keluaran": keluaran, "masukan": masukan, "net": keluaran - masukan}
