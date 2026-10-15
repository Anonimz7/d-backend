"""Seed dbn6sport: 7 members, 6 programs (termasuk p6), settings, templates.
Data klien/laporan/transaksi dibuat oleh frontend saat uji (tidak di-seed).
"""
from __future__ import annotations

import bcrypt
from sqlalchemy.orm import Session

from .models import CorrectionTemplate, Member, Program, SchedulePattern, Setting


def _pw() -> str:
    return bcrypt.hashpw(b"x", bcrypt.gensalt()).decode()


def ensure_owner(db: Session) -> None:
    # Produksi: jangan buat user demo otomatis. Owner dibuat manual via SQL.
    # Hanya pastikan tidak ada konflik jika dipanggil.
    return


def ensure_basics(db: Session) -> None:
    """Seed minimal untuk produksi: hanya settings esensial (targets, acl).
    Tidak membuat user/program/template demo."""
    if not db.query(Setting).filter_by(key="targets").first():
        db.add(Setting(key="targets", value={"rev": 45000000, "klien": 5, "retensi": 75, "koreksi": 90}))
    if not db.query(Setting).filter_by(key="acl").first():
        db.add(Setting(key="acl", value={
            "admin": {"beranda": "full", "klien": "full", "coach": "full", "koreksi": "full",
                      "program": "full", "pesan": "full", "absensi": "full", "komisi": "mask",
                      "keuangan": "none", "laporan": "mask", "anggota": "full",
                      "setting": "full", "progress": "none"},
            "head": {"beranda": "full", "klien": "full", "coach": "full", "koreksi": "full",
                     "program": "full", "pesan": "full", "absensi": "full", "komisi": "none",
                     "keuangan": "none", "laporan": "mask", "anggota": "none",
                     "setting": "full", "progress": "none"},
            "coach": {"beranda": "full", "klien": "full", "coach": "full", "koreksi": "none",
                      "program": "full", "pesan": "full", "absensi": "full", "komisi": "full",
                      "keuangan": "none", "laporan": "none", "anggota": "none",
                      "setting": "full", "progress": "none"},
        }))


def seed_all(db: Session) -> None:
    ensure_owner(db)
    members = [
        ("u2", "Sari Anggraini", "admin", "sari.admin", "sari@numbersix.example", "0812-3456-7802", ""),
        ("u3", "Hendra Kusuma", "head", "hendra", "hendra@numbersix.example", "0812-3456-7803", "GBK Senayan"),
        ("u4", "Dimas Pratama", "coach", "dimas", "dimas@numbersix.example", "0812-3456-7804", "GBK Senayan"),
        ("u5", "Lestari Ayu", "coach", "lestari", "lestari@numbersix.example", "0812-3456-7805", "GBK Senayan"),
        ("u6", "Rangga Putra", "coach", "rangga", "rangga@numbersix.example", "0812-3456-7806", "GBK Senayan"),
        ("u7", "Maya Octaviani", "coach", "maya", "maya@numbersix.example", "0812-3456-7807", "GBK Senayan"),
    ]
    for mid, name, role, login, email, wa, loc in members:
        if not db.query(Member).filter_by(id=mid).first():
            db.add(Member(id=mid, name=name, role=role, login=login,
                          password_hash=_pw(), email=email, wa=wa, loc=loc))

    programs = [
        ("p1", "Marathon 16 Minggu", 6500000, "16 minggu", 16, 1.0, 1, 0),
        ("p2", "Half Marathon 12 Minggu", 4200000, "12 minggu", 12, 0.75, 1, 0),
        ("p3", "10K Starter 8 Minggu", 2400000, "8 minggu", 8, 0.5, 1, 0),
        ("p4", "Pace Rescue 4 Minggu", 1500000, "4 minggu", 4, 0.6, 1, 0),
        ("p5", "Private 1-on-1 Bulanan", 3500000, "per bulan", 4, 0.85, 1, 0),
        ("p6", "Paket Berdua 8 Minggu", 4000000, "8 minggu", 8, 0.6, 2, 60000),
    ]
    for pid, name, price, unit, wk, lvl, peserta, fee in programs:
        if not db.query(Program).filter_by(id=pid).first():
            db.add(Program(id=pid, name=name, price=price, unit=unit,
                           wk=wk, lvl=lvl, peserta=peserta, fee=fee))

    templates = [
        ("t1", "Pace terlalu cepat", "Halo {nama}, pace {jenis} kamu lebih cepat dari patokan. Turunkan 10-15 detik per km."),
        ("t2", "Jarak kurang", "{nama}, jarak sesi {jenis} ini kurang dari program. Kejar volume minggu ini di sesi berikutnya."),
        ("t3", "Kerja bagus", "Sesi {jenis} yang rapi, {nama}. Pace stabil dan HR terkendali. Pertahankan."),
        ("t4", "Waspada cedera", "{nama}, catatan nyeri kamu perlu diperhatikan. Kurangi intensitas 2 hari ke depan."),
        ("t5", "HR terlalu tinggi", "HR rata-rata kamu di atas zona target untuk sesi {jenis}. Perlambat langkah."),
    ]
    for tid, title, text in templates:
        if not db.query(CorrectionTemplate).filter_by(id=tid).first():
            db.add(CorrectionTemplate(id=tid, title=title, text=text))

    if not db.query(Setting).filter_by(key="targets").first():
        db.add(Setting(key="targets", value={"rev": 45000000, "klien": 5, "retensi": 75, "koreksi": 90}))
    if not db.query(Setting).filter_by(key="acl").first():
        db.add(Setting(key="acl", value={
            "admin": {"beranda": "full", "klien": "full", "coach": "full", "koreksi": "full",
                      "program": "full", "pesan": "full", "absensi": "full", "komisi": "mask",
                      "keuangan": "none", "laporan": "mask", "anggota": "full",
                      "setting": "full", "progress": "none"},
            "head": {"beranda": "full", "klien": "full", "coach": "full", "koreksi": "full",
                     "program": "full", "pesan": "full", "absensi": "full", "komisi": "none",
                     "keuangan": "none", "laporan": "mask", "anggota": "none",
                     "setting": "full", "progress": "none"},
            "coach": {"beranda": "full", "klien": "full", "coach": "full", "koreksi": "none",
                      "program": "full", "pesan": "full", "absensi": "full", "komisi": "full",
                      "keuangan": "none", "laporan": "none", "anggota": "none",
                      "setting": "full", "progress": "none"},
        }))

    # schedule patterns default untuk coach (seperti mock)
    coaches = ["u3", "u4", "u5", "u6", "u7"]
    for ci, cid in enumerate(coaches):
        for d in range(7):
            if db.query(SchedulePattern).filter_by(coach_id=cid, day=d).first():
                continue
            if d < 5:
                slots = ['05:30', '06:30', '17:30', '18:30'] if ci % 2 else ['06:30', '07:30', '16:30', '17:30']
            elif d == 5:
                slots = ['05:30', '06:30', '07:30']
            else:
                slots = ['05:30', '06:30'] if ci < 3 else []
            db.add(SchedulePattern(coach_id=cid, day=d, slots=slots))
    db.commit()
