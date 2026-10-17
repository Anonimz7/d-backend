"""GET/POST /attendance, GET/PUT /coach-profiles, GET/POST /share-links"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import get_current_user

router = APIRouter()


class AttendanceIn(BaseModel):
    date: str
    coach_id: str
    time: str
    status: str
    by_name: Optional[str] = None
    at: Optional[str] = None


class CoachProfileIn(BaseModel):
    rating: Optional[float] = None
    reviews: Optional[int] = None
    since: Optional[str] = None
    skills: Optional[dict] = None


class ShareLinkIn(BaseModel):
    client_id: str
    date: str
    url: str


@router.get("/attendance")
def list_attendance(date: Optional[str] = None,
                    coach_id: Optional[str] = None,
                    user: models.Member = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    q = db.query(models.Attendance)
    if date:
        q = q.filter_by(date=date)
    if coach_id:
        q = q.filter_by(coach_id=coach_id)
    rows = q.all()
    return {"data": [
        {"id": r.id, "date": r.date, "coach_id": r.coach_id, "time": r.time,
         "status": r.status, "by_name": r.by_name, "at": r.at}
        for r in rows
    ]}


@router.post("/attendance", status_code=201)
def save_attendance(body: AttendanceIn,
                    user: models.Member = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    rid = f"{body.date}|{body.coach_id}|{body.time}"
    r = db.query(models.Attendance).filter_by(id=rid).first()
    if r:
        r.status = body.status
        r.by_name = body.by_name
        r.at = body.at
    else:
        r = models.Attendance(
            id=rid, date=body.date, coach_id=body.coach_id, time=body.time,
            status=body.status, by_name=body.by_name, at=body.at)
        db.add(r)
    db.commit()
    return {"data": {"id": rid}}


@router.get("/coach-profiles")
def list_coach_profiles(user: models.Member = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    rows = db.query(models.CoachProfile).all()
    return {"data": [
        {"coach_id": r.coach_id, "rating": r.rating, "reviews": r.reviews,
         "since": r.since, "skills": r.skills or {}}
        for r in rows
    ]}


@router.put("/coach-profiles/{coach_id}")
def save_coach_profile(coach_id: str, body: CoachProfileIn,
                       user: models.Member = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    r = db.query(models.CoachProfile).filter_by(coach_id=coach_id).first()
    if not r:
        r = models.CoachProfile(coach_id=coach_id)
        db.add(r)
    if body.rating is not None:
        r.rating = body.rating
    if body.reviews is not None:
        r.reviews = body.reviews
    if body.since is not None:
        r.since = body.since
    if body.skills is not None:
        r.skills = body.skills
    db.commit()
    return {"ok": True}


@router.get("/share-links")
def list_share_links(user: models.Member = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    rows = db.query(models.ShareLink).order_by(models.ShareLink.date.desc()).all()
    return {"data": [
        {"id": r.id, "client_id": r.client_id, "date": r.date, "url": r.url,
         "fix_text": r.fix_text, "fix_by": r.fix_by,
         "fix_at": r.fix_at.isoformat() if r.fix_at else None}
        for r in rows
    ]}


@router.post("/share-links", status_code=201)
def save_share_link(body: ShareLinkIn,
                    user: models.Member = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    import uuid
    # upsert per client+date
    r = db.query(models.ShareLink).filter_by(
        client_id=body.client_id, date=body.date).first()
    if r:
        r.url = body.url
    else:
        r = models.ShareLink(
            id=uuid.uuid4().hex[:16], client_id=body.client_id,
            date=body.date, url=body.url)
        db.add(r)
    db.commit()
    return {"data": {"id": r.id}}


@router.patch("/share-links/{lid}")
def patch_share_link(lid: str, body: dict,
                     user: models.Member = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    from datetime import datetime
    r = db.query(models.ShareLink).filter_by(id=lid).first()
    if not r and "|" in lid:
        # Fallback: cari by client_id|date
        parts = lid.split("|")
        if len(parts) == 2:
            r = db.query(models.ShareLink).filter_by(client_id=parts[0], date=parts[1]).first()
    if not r:
        return {"data": {"ok": False}}
    if "fix_text" in body:
        r.fix_text = body["fix_text"]
        r.fix_by = user.id
        r.fix_at = datetime.utcnow()
    db.commit()
    return {"data": {"ok": True}}
