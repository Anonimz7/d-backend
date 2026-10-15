"""GET/PATCH /settings, GET /correction-templates"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user

router = APIRouter()


@router.get("/settings")
def get_settings(user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    out = {}
    for s in db.query(models.Setting).all():
        out[s.key] = s.value
    return {"data": out}


@router.patch("/settings")
def patch_settings(body: schemas.SettingsPatch,
                   user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        s = db.query(models.Setting).filter_by(key=k).first()
        if s:
            s.value = v
        else:
            db.add(models.Setting(key=k, value=v))
    db.commit()
    return get_settings(user, db)


@router.get("/correction-templates")
def get_templates(user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return {"data": [{"id": t.id, "title": t.title, "text": t.text}
                     for t in db.query(models.CorrectionTemplate).all()]}
