"""CRUD perusahaan (relasional, tanpa JSON payload)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import require_perm

router = APIRouter(prefix="/companies", tags=["companies"])


def _meta(c: models.Company) -> dict:
    return {"id": c.id, "name": c.name, "industry": c.industry or "", "color": c.color, "initial": c.initial}


@router.get("", response_model=list[schemas.CompanyMeta])
def list_companies(db: Session = Depends(get_db), _t: dict = Depends(require_perm("view"))):
    return [_meta(c) for c in db.query(models.Company).order_by(models.Company.name).all()]


@router.post("", response_model=schemas.CompanyMeta)
def create_company(body: schemas.CompanyCreate, db: Session = Depends(get_db), _t: dict = Depends(require_perm("create"))):
    cid = "co_" + uuid.uuid4().hex[:8]
    c = models.Company(id=cid, name=body.name, industry=body.industry, color=body.color,
                       initial=body.name[:2].upper())
    db.add(c)
    db.commit()
    return _meta(c)


@router.post("/sync")
def sync_meta(body: schemas.MetaSync, _t: dict = Depends(require_perm("create"))):
    # Dipakai mode localStorage->server: klien mendorong daftar meta.
    return {"ok": True, "count": len(body.companies)}


@router.get("/{company_id}")
def get_company(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_perm("view"))):
    c = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Perusahaan tidak ditemukan")
    # Kembalikan meta + ringkasan relasional (pengganti payload)
    n_coa = db.query(models.CoaAccount).filter(models.CoaAccount.company_id == company_id).count()
    n_journal = db.query(models.Journal).filter(models.Journal.company_id == company_id).count()
    n_sales = db.query(models.SalesInvoice).filter(models.SalesInvoice.company_id == company_id).count()
    n_purch = db.query(models.PurchaseInvoice).filter(models.PurchaseInvoice.company_id == company_id).count()
    return {**_meta(c), "counts": {"coa": n_coa, "journal": n_journal, "sales": n_sales, "purchases": n_purch}}


@router.put("/{company_id}")
def save_company(company_id: str, body: schemas.CompanyPayload, db: Session = Depends(get_db),
                 _t: dict = Depends(require_perm("edit"))):
    c = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not c:
        c = models.Company(id=company_id, name=body.name)
        db.add(c)
    c.name = body.name
    c.industry = body.industry
    c.color = body.color
    c.initial = body.initial
    db.commit()
    return {"ok": True}
