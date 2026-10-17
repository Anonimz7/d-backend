"""Pesan: team, DM, broadcast, tandai dibaca."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(m):
    return {"id": m.id, "w": m.sender, "text": m.text,
            "t": m.t.isoformat() if m.t else None,
            "to": m.to_text, "by": m.sender}


@router.get("/messages/team")
def get_team(user: models.Member = Depends(get_current_user),
             db: Session = Depends(get_db)):
    ms = db.query(models.Message).filter_by(kind="team")\
        .order_by(models.Message.t).all()
    return {"data": [_out(m) for m in ms]}


@router.post("/messages/team", status_code=201)
def post_team(body: schemas.MessageIn,
              user: models.Member = Depends(get_current_user),
              db: Session = Depends(get_db)):
    m = models.Message(id=next_id(db, models.Message, "m"), kind="team", sender=user.id,
                       text=body.text)
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.get("/messages/dm/{cid}")
def get_dm(cid: str, user: models.Member = Depends(get_current_user),
           db: Session = Depends(get_db)):
    ms = db.query(models.Message).filter_by(kind="dm", thread_id=cid)\
        .order_by(models.Message.t).all()
    return {"data": [_out(m) for m in ms]}


@router.post("/messages/dm/{cid}", status_code=201)
def post_dm(cid: str, body: schemas.MessageIn,
            user: models.Member = Depends(get_current_user),
            db: Session = Depends(get_db)):
    m = models.Message(id=next_id(db, models.Message, "m"), kind="dm", thread_id=cid,
                       sender=user.id, text=body.text)
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.get("/messages/broadcasts")
def get_broadcasts(user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    ms = db.query(models.Message).filter_by(kind="broadcast")\
        .order_by(models.Message.t.desc()).all()
    return {"data": [_out(m) for m in ms]}


@router.post("/messages/broadcasts", status_code=201)
def post_broadcast(body: schemas.BroadcastIn,
                   user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    m = models.Message(id=next_id(db, models.Message, "b"), kind="broadcast",
                       sender=user.id, to_text=body.to, text=body.text)
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.post("/messages/{mid}/read")
def mark_read(mid: str, user: models.Member = Depends(get_current_user),
              db: Session = Depends(get_db)):
    m = db.query(models.Message).filter_by(id=mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="Pesan tidak ada")
    m.read_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}
