"""GET/POST /activity"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user

router = APIRouter()


@router.get("/activity")
def list_activity(user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    rows = db.query(models.ActivityLog)\
        .order_by(models.ActivityLog.t.desc()).limit(50).all()
    return {"data": [{"t": r.t.isoformat() if r.t else None,
                      "who": r.who, "text": r.text} for r in rows]}


@router.post("/activity", status_code=201)
def post_activity(body: schemas.ActivityIn,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    r = models.ActivityLog(who=user.name, text=body.text)
    db.add(r); db.commit(); db.refresh(r)
    return {"data": {"t": r.t.isoformat() if r.t else None,
                     "who": r.who, "text": r.text}}
