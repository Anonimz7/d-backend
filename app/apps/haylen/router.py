"""Router gabungan Haylen.

TANPA prefix global — mount point di main.py yang menangani namespace
(`/api/haylen`). Urutan include sama seperti main.py aslinya.
"""
from fastapi import APIRouter

from .routers import (
    accounts,
    auth,
    coach,
    dashboard,
    fasilitas,
    jadwal,
    kelas_program,
    laporan,
    member,
    pengaturan,
    transaksi,
)

router = APIRouter()

for _r in (auth, accounts, dashboard, member, kelas_program, coach, jadwal, transaksi, laporan, fasilitas, pengaturan):
    router.include_router(_r.router)
