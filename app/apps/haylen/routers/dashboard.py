"""Endpoint /dashboard/summary. Nilai omzet disembunyikan untuk tier tanpa hak lihat omzet."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db

from ..access import feature_of, require_menu
from ..models import Coach, Member, Program, Schedule, Transaction, User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

BULAN_ID = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _fmt_tanggal(tgl):
    """'YYYY-MM-DD' -> '12 Okt 2026'."""
    try:
        y, m, d = str(tgl).split("-")
        return f"{int(d)} {BULAN_ID[int(m) - 1]} {y}"
    except (ValueError, AttributeError, IndexError):
        return tgl or "-"


def _rupiah(n):
    return "Rp" + f"{int(n or 0):,}".replace(",", ".")


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(require_menu("dashboard", "GET"))):
    total_member = db.query(func.count(Member.id)).scalar() or 0
    total_coach = db.query(func.count(Coach.id)).scalar() or 0
    total_kelas = db.query(func.count(Schedule.id)).scalar() or 0

    # Distribusi member per program
    dist_rows = db.query(Member.program, func.count(Member.id)).group_by(Member.program).all()
    palette = ["#fdb827", "#a855f7", "#34c98b", "#3b82f6", "#f472b6"]
    distribution = [
        {
            "name": name or "-",
            "count": count,
            "percent": round(count * 100 / total_member) if total_member else 0,
            "color": palette[i % len(palette)],
        }
        for i, (name, count) in enumerate(dist_rows)
    ]

    # Kehadiran: % jadwal bertanda "Hadir" dari yang sudah diabsen (bukan "Belum")
    hadir = db.query(func.count(Schedule.id)).filter(Schedule.absensi == "Hadir").scalar() or 0
    terabsen = db.query(func.count(Schedule.id)).filter(Schedule.absensi != "Belum").scalar() or 0
    kehadiran_pct = round(hadir * 100 / terabsen) if terabsen else 0

    # Aktivitas terbaru: 6 transaksi terakhir + 4 member terbaru, urut waktu desc
    recent_tx = (
        db.query(Transaction)
        .order_by(desc(Transaction.tanggal), desc(Transaction.id))
        .limit(6)
        .all()
    )
    recent_members = db.query(Member).order_by(desc(Member.id)).limit(4).all()
    activities = []
    for t in recent_tx:
        masuk = t.tipe == "Pemasukan"
        activities.append(
            {
                "icon": "transaksi",
                "tone": "c-green" if masuk else "c-orange",
                "title": t.keterangan or t.member or "-",
                "sub": f"{t.tipe} · {_rupiah(t.jumlah)}",
                "time": _fmt_tanggal(t.tanggal),
                "sort": str(t.tanggal or ""),
            }
        )
    for m in recent_members:
        activities.append(
            {
                "icon": "member",
                "tone": "c-blue",
                "title": f"Member baru: {m.nama}",
                "sub": m.program or "-",
                "time": _fmt_tanggal(m.bergabung),
                "sort": str(m.bergabung or ""),
            }
        )
    activities.sort(key=lambda a: a["sort"], reverse=True)
    activities = [{k: v for k, v in a.items() if k != "sort"} for a in activities[:8]]

    result = {
        "stats": {
            "totalMember": {"value": total_member, "trend": 0, "note": "total terdaftar"},
            "kelasAktif": {"value": total_kelas, "trend": 0, "note": "jadwal kelas"},
            "totalCoach": {"value": total_coach, "trend": 0, "note": "tidak berubah"},
            "kehadiran": {
                "value": kehadiran_pct,
                "trend": 0,
                "note": "dari jadwal terabsen" if terabsen else "belum ada data absensi",
                "hasData": bool(terabsen),
            },
        },
        "distribution": distribution,
        "popular": [
            {"name": d["name"], "members": d["count"], "color": d["color"], "rank": d["color"]}
            for d in sorted(distribution, key=lambda x: -x["count"])[:5]
        ],
        "activities": activities,
    }

    # Data keuangan hanya untuk tier yang berhak
    if feature_of(user, "lihat_omzet_laba") != "none":
        today = date.today()
        prefix = today.strftime("%Y-%m")
        txs = db.query(Transaction).filter(Transaction.tanggal.like(prefix + "%")).all()
        income = sum(t.jumlah for t in txs if t.tipe == "Pemasukan")
        expense = sum(t.jumlah for t in txs if t.tipe == "Pengeluaran")

        # Tren pendapatan 6 bulan terakhir (dalam juta rupiah, sesuai skala chart frontend)
        labels, values = [], []
        y, m = today.year, today.month
        for _ in range(6):
            pref = f"{y:04d}-{m:02d}"
            month_income = (
                db.query(func.coalesce(func.sum(Transaction.jumlah), 0))
                .filter(Transaction.tipe == "Pemasukan", Transaction.tanggal.like(pref + "%"))
                .scalar()
                or 0
            )
            labels.append(BULAN_ID[m - 1])
            values.append(round(month_income / 1_000_000, 1))
            m -= 1
            if m == 0:
                m, y = 12, y - 1
        labels.reverse()
        values.reverse()

        result["stats"]["pendapatan"] = {"value": income, "trend": 0, "note": "dibanding bulan lalu"}
        result["revenueTrend"] = {"labels": labels, "values": values}
        result["finance"] = {
            "period": "Bulan " + today.strftime("%B %Y"),
            "rows": [
                {"label": "Pendapatan", "amount": income, "trend": 0, "icon": "member", "tone": "c-green"},
                {"label": "Biaya Operasional", "amount": expense, "trend": 0, "icon": "receipt", "tone": "c-orange"},
            ],
            "netProfit": income - expense,
            "netTrend": 0,
        }
    return result
