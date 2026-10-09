"""Endpoint /reports/summary (ringkasan laporan bisnis)."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db

from ..access import feature_of, require_menu
from ..models import Member, Schedule, Transaction, User

router = APIRouter(prefix="/reports", tags=["laporan"])


@router.get("/summary")
def report_summary(db: Session = Depends(get_db), user: User = Depends(require_menu("laporan", "GET"))):
    data = {
        "total_member": db.query(func.count(Member.id)).scalar() or 0,
        "member_aktif": db.query(func.count(Member.id)).filter(Member.status == "Aktif").scalar() or 0,
        "jumlah_jadwal": db.query(func.count(Schedule.id)).scalar() or 0,
    }
    if feature_of(user, "laporan_bisnis") == "full":
        income = db.query(func.coalesce(func.sum(Transaction.jumlah), 0)).filter(Transaction.tipe == "Pemasukan").scalar()
        expense = db.query(func.coalesce(func.sum(Transaction.jumlah), 0)).filter(Transaction.tipe == "Pengeluaran").scalar()
        data.update({"pemasukan": income, "pengeluaran": expense, "laba": income - expense})
    return data
