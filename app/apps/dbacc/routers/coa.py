"""CRUD Chart of Accounts."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import require_perm

router = APIRouter(prefix="/companies/{company_id}/coa", tags=["coa"])


@router.get("")
def list_coa(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_perm("view"))):
    rows = db.query(models.CoaAccount).filter(
        models.CoaAccount.company_id == company_id
    ).order_by(models.CoaAccount.code).all()
    return [{"id": r.id, "code": r.code, "name": r.name, "type": r.type,
             "normal": r.normal, "is_active": r.is_active} for r in rows]


@router.post("")
def create_coa(company_id: str, body: dict, db: Session = Depends(get_db),
              _t: dict = Depends(require_perm("create"))):
    acc = models.CoaAccount(
        company_id=company_id,
        code=body.get("code", ""),
        name=body.get("name", ""),
        type=body.get("type", "Aset"),
        normal=body.get("normal", "debit"),
        is_active=body.get("is_active", True),
    )
    db.add(acc)
    db.commit()
    return {"ok": True, "id": acc.id}


@router.put("/{account_id}")
def update_coa(company_id: str, account_id: str, body: dict, db: Session = Depends(get_db),
               _t: dict = Depends(require_perm("edit"))):
    acc = db.query(models.CoaAccount).filter(
        models.CoaAccount.id == account_id,
        models.CoaAccount.company_id == company_id,
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan")
    for f in ("code", "name", "type", "normal", "is_active"):
        if f in body:
            setattr(acc, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{account_id}")
def delete_coa(company_id: str, account_id: str, db: Session = Depends(get_db),
               _t: dict = Depends(require_perm("delete"))):
    acc = db.query(models.CoaAccount).filter(
        models.CoaAccount.id == account_id,
        models.CoaAccount.company_id == company_id,
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan")
    # Cegah hapus bila sudah dipakai di jurnal
    used = db.query(models.JournalLine).filter(models.JournalLine.account_id == account_id).count()
    if used:
        raise HTTPException(status_code=400, detail="Akun sudah dipakai di jurnal, nonaktifkan saja")
    db.delete(acc)
    db.commit()
    return {"ok": True}
