"""Portal klien publik (tanpa token login).

Kredensial aksesnya adalah portal_token ACAK milik klien (link #c=<token>),
BUKAN uid (N6-xxxx bersifat urut dan mudah ditebak).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi import Depends

from app.core.database import get_db

from .. import models, schemas
from ..ids import next_id
from .clients import _out as _out_client, _out_rep
from .messages import _out as _out_msg

router = APIRouter()


class PortalLinkIn(BaseModel):
    date: str
    url: str


def _by_token(db: Session, token: str):
    c = db.query(models.Client).filter_by(portal_token=token).first()
    if not c:
        raise HTTPException(status_code=404, detail="Link tidak valid")
    return c


def _out_link(r):
    return {"id": r.id, "client_id": r.client_id, "date": r.date, "url": r.url,
            "fix_text": r.fix_text, "fix_by": r.fix_by,
            "fix_at": r.fix_at.isoformat() if r.fix_at else None}


@router.get("/portal/{token}")
def portal_dashboard(token: str, db: Session = Depends(get_db)):
    c = _by_token(db, token)
    pr = db.query(models.Program).filter_by(id=c.program_id).first()
    reps = db.query(models.Report).filter_by(client_id=c.id)\
        .order_by(models.Report.date).all()
    msgs = db.query(models.Message).filter_by(kind="dm", thread_id=c.id)\
        .order_by(models.Message.t).all()
    links = db.query(models.ShareLink).filter_by(client_id=c.id)\
        .order_by(models.ShareLink.date).all()
    # Nama yang dibutuhkan tampilan portal: coach klien + pengirim pesan.
    people_ids = {c.coach_id} | {m.sender for m in msgs}
    people = []
    for mid in people_ids:
        if not mid or mid == c.id:
            continue
        mb = db.query(models.Member).filter_by(id=mid).first()
        if mb:
            people.append({"id": mb.id, "name": mb.name})
    return {"data": {
        "client": _out_client(c),
        "program": {"id": pr.id, "name": pr.name, "price": pr.price} if pr else None,
        "reports": [_out_rep(r) for r in reps],
        "messages": [_out_msg(m) for m in msgs],
        "links": [_out_link(r) for r in links],
        "people": people,
    }}


@router.post("/portal/{token}/messages", status_code=201)
def portal_message(token: str, body: schemas.MessageIn,
                   db: Session = Depends(get_db)):
    c = _by_token(db, token)
    m = models.Message(id=next_id(db, models.Message, "m"), kind="dm",
                       thread_id=c.id, sender=c.id, text=body.text)
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out_msg(m)}


@router.post("/portal/{token}/links", status_code=201)
def portal_link(token: str, body: PortalLinkIn,
                db: Session = Depends(get_db)):
    """Klien menyetor link hasil latihan dari portal publik (upsert per tanggal)."""
    import uuid
    c = _by_token(db, token)
    r = db.query(models.ShareLink).filter_by(
        client_id=c.id, date=body.date).first()
    if r:
        r.url = body.url
    else:
        r = models.ShareLink(id=uuid.uuid4().hex[:16], client_id=c.id,
                             date=body.date, url=body.url)
        db.add(r)
    db.commit()
    return {"data": {"id": r.id}}
