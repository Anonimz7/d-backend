"""GET/POST/DELETE /makeup — sesi pengganti hasil undur (tanggal + jam pilihan)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(t):
    return {"id": t.id, "client_id": t.client_id, "coach_id": t.coach_id,
            "date": t.date.isoformat() if t.date else None,
            "time": t.time, "request_id": t.request_id}


@router.get("/makeup")
def list_makeup(user: models.Member = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return {"data": [_out(t) for t in db.query(models.Makeup).all()]}


@router.post("/makeup", status_code=201)
def create_makeup(body: schemas.MakeupIn,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(id=body.client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ditemukan")
    t = models.Makeup(id=next_id(db, models.Makeup, "mk"), **body.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return {"data": _out(t)}


@router.delete("/makeup/{mid}")
def delete_makeup(mid: str,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    t = db.query(models.Makeup).filter_by(id=mid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Sesi pengganti tidak ditemukan")
    db.delete(t); db.commit()
    return {"data": {"deleted": mid}}
