"""Portal klien publik (tanpa token)."""
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db

from .. import models, schemas
from .clients import _out as _out_client, _out_rep
from .messages import _out as _out_msg, _cnt as _msg_cnt

router = APIRouter()


@router.get("/portal/{uid}")
def portal_dashboard(uid: str, db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(uid=uid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Link tidak valid")
    pr = db.query(models.Program).filter_by(id=c.program_id).first()
    reps = db.query(models.Report).filter_by(client_id=c.id)\
        .order_by(models.Report.date).all()
    msgs = db.query(models.Message).filter_by(kind="dm", thread_id=c.id)\
        .order_by(models.Message.t).all()
    return {"data": {
        "client": _out_client(c),
        "program": {"id": pr.id, "name": pr.name, "price": pr.price} if pr else None,
        "reports": [_out_rep(r) for r in reps],
        "messages": [_out_msg(m) for m in msgs],
    }}


@router.post("/portal/{uid}/messages", status_code=201)
def portal_message(uid: str, body: schemas.MessageIn,
                   db: Session = Depends(get_db)):
    c = db.query(models.Client).filter_by(uid=uid).first()
    if not c:
        raise HTTPException(status_code=404, detail="Link tidak valid")
    _msg_cnt["m"] += 1
    m = models.Message(id=f"m{_msg_cnt['m']}", kind="dm",
                       thread_id=c.id, sender=c.id, text=body.text)
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out_msg(m)}
