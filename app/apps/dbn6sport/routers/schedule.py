"""GET /schedule, POST/DELETE /bookings"""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user

router = APIRouter()
_cnt = {"bk": 100}


@router.get("/schedule")
def get_schedule(coach_id: Optional[str] = None,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    qry = db.query(models.SchedulePattern)
    if coach_id:
        qry = qry.filter_by(coach_id=coach_id)
    patterns = {}
    for p in qry.all():
        patterns.setdefault(p.coach_id, {})[p.day] = p.slots or []
    # frontend expects list per day 0..6
    for cid in patterns:
        patterns[cid] = [patterns[cid].get(d, []) for d in range(7)]
    bq = db.query(models.Booking)
    if coach_id:
        bq = bq.filter_by(coach_id=coach_id)
    bookings = [{"id": b.id, "coach_id": b.coach_id, "client_id": b.client_id,
                 "day": b.day, "time": b.time} for b in bq.all()]
    return {"patterns": patterns, "bookings": bookings}


@router.post("/bookings", status_code=201)
def create_booking(body: schemas.BookingIn,
                   user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _cnt["bk"] += 1
    b = models.Booking(id=f"bk{_cnt['bk']}", **body.model_dump())
    db.add(b); db.commit(); db.refresh(b)
    return {"data": {"id": b.id, "coach_id": b.coach_id, "client_id": b.client_id,
                     "day": b.day, "time": b.time}}


@router.delete("/bookings/{bid}")
def delete_booking(bid: str, user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    db.query(models.Booking).filter_by(id=bid).delete()
    db.commit()
    return {"ok": True}
