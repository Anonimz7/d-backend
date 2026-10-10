"""Transaksi ke tabel relasional (migrasi dari JSON payload).

Path endpoint tidak berubah agar frontend tetap kompatibel.
"""
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import require_menu, require_perm

router = APIRouter(prefix="/companies/{company_id}", tags=["transactions"])

COLLUMNS = {
    "sales": "penjualan",
    "purchases": "pembelian",
    "cashbank": "kasbank",
    "journal": "jurnal",
}


def _company(db: Session, company_id: str) -> models.Company:
    c = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Perusahaan tidak ditemukan")
    return c


def _parse_date(v) -> date:
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v:
        return datetime.strptime(v[:10], "%Y-%m-%d").date()
    return date.today()


@router.get("/journal")
def list_journal(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("jurnal"))):
    _company(db, company_id)
    journals = db.query(models.Journal).filter(
        models.Journal.company_id == company_id
    ).order_by(models.Journal.date.desc()).all()
    result = []
    for j in journals:
        lines = db.query(models.JournalLine, models.CoaAccount).join(
            models.CoaAccount, models.JournalLine.account_id == models.CoaAccount.id
        ).filter(models.JournalLine.journal_id == j.id).all()
        result.append({
            "id": j.id,
            "date": j.date.isoformat() if j.date else None,
            "description": j.description,
            "ref_no": j.ref_no,
            "lines": [
                {"account": acc.code, "account_name": acc.name,
                 "debit": float(ln.debit or 0), "credit": float(ln.credit or 0)}
                for ln, acc in lines
            ],
        })
    return result


@router.get("/sales")
def list_sales(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("penjualan"))):
    _company(db, company_id)
    rows = db.query(models.SalesInvoice).filter(
        models.SalesInvoice.company_id == company_id
    ).order_by(models.SalesInvoice.date.desc()).all()
    return [{"id": r.id, "invoice_no": r.invoice_no, "date": r.date.isoformat() if r.date else None,
             "total": float(r.total or 0), "status": r.status} for r in rows]


@router.get("/purchases")
def list_purchases(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("pembelian"))):
    _company(db, company_id)
    rows = db.query(models.PurchaseInvoice).filter(
        models.PurchaseInvoice.company_id == company_id
    ).order_by(models.PurchaseInvoice.date.desc()).all()
    return [{"id": r.id, "invoice_no": r.invoice_no, "date": r.date.isoformat() if r.date else None,
             "total": float(r.total or 0), "status": r.status} for r in rows]


@router.get("/cashbank")
def list_cashbank(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("kasbank"))):
    _company(db, company_id)
    rows = db.query(models.CashBankTransaction).filter(
        models.CashBankTransaction.company_id == company_id
    ).order_by(models.CashBankTransaction.date.desc()).all()
    return [{"id": r.id, "date": r.date.isoformat() if r.date else None, "direction": r.direction,
             "amount": float(r.amount or 0), "description": r.description} for r in rows]


def _create_journal(db: Session, company_id: str, body: dict) -> dict:
    j = models.Journal(
        company_id=company_id,
        date=_parse_date(body.get("date")),
        description=body.get("description", body.get("keterangan", "")),
        ref_no=body.get("ref_no", body.get("no_bukti", "")),
    )
    db.add(j)
    db.flush()
    for line in body.get("lines", []):
        # cari account by code
        acc = db.query(models.CoaAccount).filter(
            models.CoaAccount.company_id == company_id,
            models.CoaAccount.code == line.get("account"),
        ).first()
        if not acc:
            raise HTTPException(status_code=400, detail=f"Akun tidak ditemukan: {line.get('account')}")
        db.add(models.JournalLine(
            journal_id=j.id,
            account_id=acc.id,
            debit=Decimal(str(line.get("debit") or 0)),
            credit=Decimal(str(line.get("credit") or 0)),
        ))
    db.commit()
    return {"ok": True, "id": j.id, "menu": "jurnal"}


def _create_sales(db: Session, company_id: str, body: dict) -> dict:
    inv = models.SalesInvoice(
        company_id=company_id,
        invoice_no=body.get("invoice_no", body.get("no", "")),
        date=_parse_date(body.get("date", body.get("tanggal"))),
        total=Decimal(str(body.get("total") or 0)),
        status=body.get("status", "draft"),
    )
    # simpan field lain sebagai baris generik bila ada
    db.add(inv)
    db.flush()
    for item in body.get("items", []):
        db.add(models.SalesInvoiceLine(
            invoice_id=inv.id,
            description=item.get("description", item.get("deskripsi", "")),
            qty=Decimal(str(item.get("qty", 1))),
            price=Decimal(str(item.get("price", item.get("harga", 0)))),
            subtotal=Decimal(str(item.get("subtotal", 0))),
        ))
    db.commit()
    return {"ok": True, "id": inv.id, "menu": "penjualan"}


def _create_purchase(db: Session, company_id: str, body: dict) -> dict:
    inv = models.PurchaseInvoice(
        company_id=company_id,
        invoice_no=body.get("invoice_no", body.get("no", "")),
        date=_parse_date(body.get("date", body.get("tanggal"))),
        total=Decimal(str(body.get("total") or 0)),
        status=body.get("status", "draft"),
    )
    db.add(inv)
    db.flush()
    for item in body.get("items", []):
        db.add(models.PurchaseInvoiceLine(
            invoice_id=inv.id,
            description=item.get("description", item.get("deskripsi", "")),
            qty=Decimal(str(item.get("qty", 1))),
            price=Decimal(str(item.get("price", item.get("harga", 0)))),
            subtotal=Decimal(str(item.get("subtotal", 0))),
        ))
    db.commit()
    return {"ok": True, "id": inv.id, "menu": "pembelian"}


def _create_cashbank(db: Session, company_id: str, body: dict) -> dict:
    txn = models.CashBankTransaction(
        company_id=company_id,
        date=_parse_date(body.get("date", body.get("tanggal"))),
        direction=body.get("direction", body.get("tipe", "masuk")),
        amount=Decimal(str(body.get("amount", body.get("jumlah", 0)))),
        description=body.get("description", body.get("keterangan", "")),
        ref_no=body.get("ref_no", ""),
    )
    # account opsional — bila ada kode akun, resolve
    acc_code = body.get("account")
    if acc_code:
        acc = db.query(models.CoaAccount).filter(
            models.CoaAccount.company_id == company_id,
            models.CoaAccount.code == acc_code,
        ).first()
        if acc:
            txn.account_id = acc.id
    else:
        # fallback: akun kas pertama
        acc = db.query(models.CoaAccount).filter(
            models.CoaAccount.company_id == company_id,
        ).first()
        if acc:
            txn.account_id = acc.id
    if not txn.account_id:
        raise HTTPException(status_code=400, detail="Akun kas/bank belum dikonfigurasi")
    db.add(txn)
    db.commit()
    return {"ok": True, "id": txn.id, "menu": "kasbank"}


@router.post("/{coll}")
def append_trx(company_id: str, coll: str, body: dict, db: Session = Depends(get_db),
              _t: dict = Depends(require_perm("create"))):
    if coll not in COLLUMNS:
        raise HTTPException(status_code=404, detail="Koleksi tidak dikenal")
    _company(db, company_id)
    if coll == "journal":
        return _create_journal(db, company_id, body)
    if coll == "sales":
        return _create_sales(db, company_id, body)
    if coll == "purchases":
        return _create_purchase(db, company_id, body)
    if coll == "cashbank":
        return _create_cashbank(db, company_id, body)
    raise HTTPException(status_code=404, detail="Koleksi tidak dikenal")
