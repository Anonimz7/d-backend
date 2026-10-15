"""GET /dashboard/summary"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models
from ..access import get_current_user

router = APIRouter()


@router.get("/dashboard/summary")
def summary(user: models.Member = Depends(get_current_user),
            db: Session = Depends(get_db)):
    live = db.query(models.Client).filter(models.Client.arch.is_(None)).count()
    pend = db.query(models.Report).filter(
        models.Report.missed.is_(False),
        models.Report.correction_text.is_(None)).count()
    rev = db.query(func.sum(models.Transaction.amount))\
        .filter_by(type="in").scalar() or 0
    return {"live_clients": live, "sessions_today": db.query(models.Booking).count(),
            "pending_corrections": pend, "revenue_total": rev, "alerts": []}
