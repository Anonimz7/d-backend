"""GET/POST /requests, PATCH /requests/{id}"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(r):
    return {"id": r.id, "type": r.type, "who": r.who,
            "date": r.date.isoformat() if r.date else None,
            "date2": r.date2.isoformat() if r.date2 else None,
            "detail": r.detail, "status": r.status}


@router.get("/requests")
def list_requests(status: Optional[str] = None, type: Optional[str] = None,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    qry = db.query(models.Request)
    if status: qry = qry.filter_by(status=status)
    if type: qry = qry.filter_by(type=type)
    return {"data": [_out(r) for r in qry.all()]}


@router.post("/requests", status_code=201)
def create_request(body: schemas.RequestIn,
                   user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    r = models.Request(id=next_id(db, models.Request, "r"), who=user.id,
                       status="Menunggu", **body.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return {"data": _out(r)}


@router.patch("/requests/{rid}")
def patch_request(rid: str, body: schemas.RequestPatch,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    r = db.query(models.Request).filter_by(id=rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Pengajuan tidak ada")
    if body.status:
        r.status = body.status
    db.commit(); db.refresh(r)
    return {"data": _out(r)}
