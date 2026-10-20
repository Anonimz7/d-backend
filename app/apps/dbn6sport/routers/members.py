"""GET/POST /members, PATCH /members/{id}"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(m):
    return {"id": m.id, "name": m.name, "role": m.role, "login": m.login,
            "email": m.email, "wa": m.wa, "loc": m.loc}


@router.get("/members")
def list_members(user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return {"data": [_out(m) for m in db.query(models.Member).all()]}


@router.post("/members", status_code=201)
def create_member(body: schemas.MemberIn,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    pw = body.password or "x"
    m = models.Member(id=next_id(db, models.Member, "m"), name=body.name, role=body.role,
                      login=body.login, email=body.email, wa=body.wa or "",
                      loc=body.loc or "",
                      password_hash=bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.patch("/members/{mid}")
def patch_member(mid: str, body: schemas.MemberPatch,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    m = db.query(models.Member).filter_by(id=mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="Anggota tidak ada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.delete("/members/{mid}", status_code=204)
def delete_member(mid: str, force: bool = False,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    m = db.query(models.Member).filter_by(id=mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="Anggota tidak ada")
    if m.id == user.id:
        raise HTTPException(status_code=400, detail="Tidak bisa hapus akun sendiri")
    if m.role == "owner":
        raise HTTPException(status_code=400, detail="Tidak bisa hapus owner")
    # Cek relasi historis: jangan hapus bila masih terkait data riwayat.
    # (Dulu hanya klien yang dicek -> relasi lain lolos dan DB menolak = HTTP 500.)
    blockers = []
    for label, model, field in (
        ("klien", models.Client, "coach_id"),
        ("booking", models.Booking, "coach_id"),
        ("absensi", models.Attendance, "coach_id"),
        ("pembayaran komisi", models.CommissionPayment, "coach_id"),
        ("transaksi", models.Transaction, "coach_id"),
        ("koreksi laporan", models.Report, "correction_by"),
    ):
        n = db.query(model).filter_by(**{field: mid}).count()
        if n:
            blockers.append(f"{n} {label}")
    if blockers and not force:
        raise HTTPException(
            status_code=400,
            detail="Tidak bisa dihapus, masih terkait: " + ", ".join(blockers)
                   + ". Pindahkan atau hapus data terkait dulu.")
    if force:
        # Hapus paksa: riwayat bernilai DILEPAS (barisnya tetap tersimpan),
        # data operasional milik anggota sendiri DIHAPUS bersamanya.
        db.query(models.Client).filter_by(coach_id=mid).update(
            {models.Client.coach_id: None}, synchronize_session=False)
        db.query(models.Transaction).filter_by(coach_id=mid).update(
            {models.Transaction.coach_id: None}, synchronize_session=False)
        db.query(models.Report).filter_by(correction_by=mid).update(
            {models.Report.correction_by: None}, synchronize_session=False)
        db.query(models.Booking).filter_by(coach_id=mid).delete()
        db.query(models.Attendance).filter_by(coach_id=mid).delete()
        db.query(models.CommissionPayment).filter_by(coach_id=mid).delete()
    # Data setup milik anggota sendiri ikut terhapus: pola jadwal + profil coach.
    db.query(models.SchedulePattern).filter_by(coach_id=mid).delete()
    db.query(models.CoachProfile).filter_by(coach_id=mid).delete()
    db.delete(m)
    db.commit()
    return None
