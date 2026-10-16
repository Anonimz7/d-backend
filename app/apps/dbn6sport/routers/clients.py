"""Clients + nested reports."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user

router = APIRouter()
_cnt = {"cl": 100, "rp": 1000}


def _out(c):
    return {"id": c.id, "uid": c.uid, "name": c.name, "program_id": c.program_id,
            "start": c.start.isoformat() if c.start else None,
            "end": c.end.isoformat() if c.end else "",
            "coach_id": c.coach_id, "cond": c.cond, "renew": c.renew,
            "hrmax": c.hrmax, "mp": c.mp,
            "arch": c.arch.isoformat() if c.arch else None,
            "note": c.note or "", "grp": c.grp,
            "share_url": c.share_url}


def _out_rep(r):
    return {"id": r.id, "client_id": r.client_id,
            "date": r.date.isoformat() if r.date else None,
            "type": r.type, "plan_km": float(r.plan_km) if r.plan_km else None,
            "km": float(r.km) if r.km else None, "pace": r.pace, "hr": r.hr,
            "rasa": r.rasa, "note": r.note or "", "missed": r.missed,
            "link_url": r.link_url,
            "correction": ({"by": r.correction_by, "text": r.correction_text,
                            "at": r.correction_at.isoformat() if r.correction_at else None}
                           if r.correction_text else None)}


@router.get("/clients")
def list_clients(status: str = "aktif", q: Optional[str] = None,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    qry = db.query(models.Client)
    if status == "aktif":
        qry = qry.filter(models.Client.arch.is_(None))
    if q:
        qry = qry.filter(models.Client.name.ilike(f"%{q}%"))
    return {"data": [_out(c) for c in qry.all()]}


@router.post("/clients", status_code=201)
def create_client(body: schemas.ClientIn,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _cnt["cl"] += 1
    n = db.query(models.Client).count()
    uid = f"N6-{1001 + n}"
    c = models.Client(id=f"cl{_cnt['cl']}", uid=uid,
                      share_url=f"https://numbersix.example/sw/{uid}",
                      **body.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return {"data": _out(c)}


@router.get("/clients/{cid}")
def get_client(cid: str, user: models.Member = Depends(get_current_user),
               db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(id=cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ada")
    return {"data": _out(c)}


@router.patch("/clients/{cid}")
def patch_client(cid: str, body: schemas.ClientPatch,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(id=cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit(); db.refresh(c)
    return {"data": _out(c)}


@router.delete("/clients/{cid}", status_code=204)
def delete_client(cid: str, user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(id=cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ada")
    db.delete(c)
    db.commit()
    return None


@router.post("/clients/{cid}/archive")
def archive_client(cid: str, user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(id=cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ada")
    c.arch = date.today()
    db.commit(); db.refresh(c)
    return {"data": _out(c)}


@router.post("/clients/{cid}/unarchive")
def unarchive_client(cid: str, user: models.Member = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(id=cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ada")
    c.arch = None
    db.commit(); db.refresh(c)
    return {"data": _out(c)}


@router.get("/clients/{cid}/reports")
def list_reports(cid: str, from_: Optional[str] = None, to: Optional[str] = None,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    qry = db.query(models.Report).filter_by(client_id=cid)
    if from_: qry = qry.filter(models.Report.date >= from_)
    if to: qry = qry.filter(models.Report.date <= to)
    return {"data": [_out_rep(r) for r in qry.order_by(models.Report.date).all()]}


@router.post("/clients/{cid}/reports", status_code=201)
def create_report(cid: str, body: schemas.ReportIn,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    _cnt["rp"] += 1
    r = models.Report(id=f"rp{_cnt['rp']}", client_id=cid, **body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return {"data": _out_rep(r)}


@router.patch("/reports/{rid}")
def patch_report(rid: str, body: schemas.ReportPatch,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    r = db.query(models.Report).filter_by(id=rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Laporan tidak ada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit(); db.refresh(r)
    return {"data": _out_rep(r)}
