"""POST /reports/{id}/correction, GET /corrections/pending"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from .clients import _out_rep

router = APIRouter()


@router.post("/reports/{rid}/correction")
def submit_correction(rid: str, body: schemas.CorrectionIn,
                      user: models.Member = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    r = db.query(models.Report).filter_by(id=rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="Laporan tidak ada")
    r.correction_by = user.id
    r.correction_text = body.text
    r.correction_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(r)
    return {"data": _out_rep(r)}


@router.get("/corrections/pending")
def pending_corrections(coach_id: Optional[str] = None,
                        user: models.Member = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    qry = db.query(models.Report).filter(
        models.Report.missed.is_(False),
        models.Report.correction_text.is_(None))
    if coach_id:
        cids = [c.id for c in db.query(models.Client.id)
                .filter_by(coach_id=coach_id).all()]
        qry = qry.filter(models.Report.client_id.in_(cids))
    return {"data": [_out_rep(r) for r in qry.all()]}
