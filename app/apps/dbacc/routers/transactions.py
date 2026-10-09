"""Append transaksi ke payload JSON perusahaan (fase 1).
Fase 2 dapat memecah ke tabel relasional tanpa mengubah path endpoint.

Salinan dari DB Acounting/backend/app/routers/transactions.py — hanya import
yang diadaptasi (access, get_db dari core). Logika & kontrak tidak berubah.
"""
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


@router.get("/journal")
def list_journal(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_menu("jurnal"))):
    return _company(db, company_id).payload.get("journal", [])


@router.post("/{coll}")
def append_trx(company_id: str, coll: str, body: dict, db: Session = Depends(get_db),
              _t: dict = Depends(require_perm("create"))):
    if coll not in COLLUMNS:
        raise HTTPException(status_code=404, detail="Koleksi tidak dikenal")
    # Menu terkait dikembalikan agar klien bisa mencocokkan hak tier.
    menu = COLLUMNS[coll]
    c = _company(db, company_id)
    payload = dict(c.payload or {})
    items = list(payload.get(coll, []))
    items.append(body)
    payload[coll] = items
    c.payload = payload
    db.commit()
    return {"ok": True, "menu": menu}
