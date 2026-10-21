"""GET/POST/DELETE /titip — Komisi Bulanan Fase C (klien titipan coach pengganti)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(t):
    return {"id": t.id, "client_id": t.client_id,
            "date": t.date.isoformat() if t.date else None,
            "from_coach": t.from_coach, "to_coach": t.to_coach,
            "time": t.time, "request_id": t.request_id}


@router.get("/titip")
def list_titip(user: models.Member = Depends(get_current_user),
               db: Session = Depends(get_db)):
    return {"data": [_out(t) for t in db.query(models.Titip).all()]}


@router.post("/titip", status_code=201)
def create_titip(body: schemas.TitipIn,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    if body.from_coach == body.to_coach:
        raise HTTPException(status_code=400,
                            detail="Coach pengganti harus berbeda dari coach pemilik klien")
    c = db.query(models.Client).filter_by(id=body.client_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Klien tidak ditemukan")
    t = models.Titip(id=next_id(db, models.Titip, "tp"), **body.model_dump())
    db.add(t); db.commit(); db.refresh(t)
    return {"data": _out(t)}


@router.delete("/titip/{tid}")
def delete_titip(tid: str,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    t = db.query(models.Titip).filter_by(id=tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="Titipan tidak ditemukan")
    db.delete(t); db.commit()
    return {"data": {"deleted": tid}}
