"""GET/POST /transactions, GET /finance/summary, GET /commissions"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(t):
    return {"id": t.id, "date": t.date.isoformat() if t.date else None,
            "type": t.type, "category": t.category, "amount": t.amount,
            "desc": t.description, "program_id": t.program_id,
            "coach_id": t.coach_id}


@router.get("/transactions")
def list_transactions(from_: Optional[str] = None, to: Optional[str] = None,
                      type: Optional[str] = None,
                      user: models.Member = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    qry = db.query(models.Transaction)
    if type: qry = qry.filter_by(type=type)
    if from_: qry = qry.filter(models.Transaction.date >= from_)
    if to: qry = qry.filter(models.Transaction.date <= to)
    return {"data": [_out(t) for t in qry.order_by(models.Transaction.date).all()]}


@router.post("/transactions", status_code=201)
def create_transaction(body: schemas.TransactionIn,
                       user: models.Member = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    d = body.model_dump()
    tx = models.Transaction(id=next_id(db, models.Transaction, "t", start=1000), description=d.pop("desc", ""),
                            **d)
    db.add(tx); db.commit(); db.refresh(tx)
    return {"data": _out(tx)}


@router.delete("/transactions/{tid}", status_code=204)
def delete_transaction(tid: str, user: models.Member = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter_by(id=tid).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaksi tidak ada")
    db.delete(tx)
    db.commit()
    return None


@router.get("/finance/summary")
def finance_summary(user: models.Member = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    inc = db.query(func.sum(models.Transaction.amount))\
        .filter_by(type="in").scalar() or 0
    exp = db.query(func.sum(models.Transaction.amount))\
        .filter_by(type="out").scalar() or 0
    ci = db.query(models.Transaction).filter_by(type="in").count()
    co = db.query(models.Transaction).filter_by(type="out").count()
    return {"income": inc, "expense": exp, "net": inc - exp,
            "count_in": ci, "count_out": co}


@router.get("/commissions")
def commissions(coach_id: Optional[str] = None,
                user: models.Member = Depends(get_current_user),
                db: Session = Depends(get_db)):
    qry = db.query(models.Transaction).filter_by(type="in")
    if coach_id:
        qry = qry.filter_by(coach_id=coach_id)
    byc = {}
    for t in qry.all():
        byc[t.coach_id or "-"] = byc.get(t.coach_id or "-", 0) + t.amount
    return {"data": [{"coach_id": k, "revenue": v, "commission": round(v * 0.2)}
                     for k, v in byc.items()]}
