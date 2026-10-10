"""CRUD master pelanggan & pemasok."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import require_perm

router = APIRouter(prefix="/companies/{company_id}", tags=["partners"])


# --- Customers ---
@router.get("/customers")
def list_customers(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_perm("view"))):
    rows = db.query(models.Customer).filter(models.Customer.company_id == company_id).order_by(models.Customer.name).all()
    return [{"id": r.id, "name": r.name, "email": r.email, "phone": r.phone, "address": r.address} for r in rows]


@router.post("/customers")
def create_customer(company_id: str, body: dict, db: Session = Depends(get_db), _t: dict = Depends(require_perm("create"))):
    c = models.Customer(company_id=company_id, name=body.get("name", ""),
                        email=body.get("email", ""), phone=body.get("phone", ""),
                        address=body.get("address", ""))
    db.add(c)
    db.commit()
    return {"ok": True, "id": c.id}


@router.delete("/customers/{customer_id}")
def delete_customer(company_id: str, customer_id: str, db: Session = Depends(get_db),
                    _t: dict = Depends(require_perm("delete"))):
    c = db.query(models.Customer).filter(models.Customer.id == customer_id,
                                          models.Customer.company_id == company_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Pelanggan tidak ditemukan")
    db.delete(c)
    db.commit()
    return {"ok": True}


# --- Suppliers ---
@router.get("/suppliers")
def list_suppliers(company_id: str, db: Session = Depends(get_db), _t: dict = Depends(require_perm("view"))):
    rows = db.query(models.Supplier).filter(models.Supplier.company_id == company_id).order_by(models.Supplier.name).all()
    return [{"id": r.id, "name": r.name, "email": r.email, "phone": r.phone, "address": r.address} for r in rows]


@router.post("/suppliers")
def create_supplier(company_id: str, body: dict, db: Session = Depends(get_db), _t: dict = Depends(require_perm("create"))):
    s = models.Supplier(company_id=company_id, name=body.get("name", ""),
                        email=body.get("email", ""), phone=body.get("phone", ""),
                        address=body.get("address", ""))
    db.add(s)
    db.commit()
    return {"ok": True, "id": s.id}


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(company_id: str, supplier_id: str, db: Session = Depends(get_db),
                    _t: dict = Depends(require_perm("delete"))):
    s = db.query(models.Supplier).filter(models.Supplier.id == supplier_id,
                                          models.Supplier.company_id == company_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Pemasok tidak ditemukan")
    db.delete(s)
    db.commit()
    return {"ok": True}
