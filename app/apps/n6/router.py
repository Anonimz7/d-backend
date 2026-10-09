from __future__ import annotations
"""Router gabungan N6. Porting dari N6/backend/app/api/v1/router.py.

URUTAN MOUNT PENTING dan dipertahankan persis seperti aslinya:

1. Path literal didaftarkan sebelum path berparameter di dalam tiap router
   (mis. /commissions/summary sebelum /commissions/{coach_id}; lihat
   __init__.py di routers/ dan urutan definisi tiap file endpoint).
2. Rute uang tetap di-mount walau hanya owner yang bisa mencapai: 403 dari
   aturan tier adalah jawaban yang lebih baik daripada 404.

Prefix "/v1" dipertahankan di sini; main.py me-mount router ini di /api/n6,
sehingga path final = /api/n6/v1/...
"""


from fastapi import APIRouter

from .routers import (
    accounts,
    athletes,
    attendance,
    auth,
    clients,
    commissions,
    corrections,
    dashboards,
    finance,
    messages,
    monitoring,
    portal,
    pricing,
    programs,
    reports,
    schedules,
    tickets,
)

router = APIRouter(prefix="/v1")

# ------------------------------------------------------------------ identity
router.include_router(auth.router)
router.include_router(auth.access_router)
router.include_router(accounts.router)

# ------------------------------------------------------------------- clients
router.include_router(clients.router)
router.include_router(schedules.router)

# ------------------------------------------------- catalogue and scheduling
router.include_router(pricing.router)
router.include_router(programs.router)

# --------------------------------------------------------------------- money
router.include_router(commissions.router)
router.include_router(finance.router)

# ------------------------------------------------------------------- support
router.include_router(tickets.router)
router.include_router(messages.router)
router.include_router(attendance.router)
router.include_router(dashboards.router)

# -------------------------------------------------------------- head coach
router.include_router(monitoring.router)
router.include_router(corrections.router)
router.include_router(athletes.router)

# ------------------------------------------------------------------ reports
router.include_router(reports.router)

# ------------------------------------------------------------------- portal
# Terakhir, dan tanpa dependency require(): /portal self-scoped dari token,
# jadi gating by menu hanya menambah salinan aturan yang lebih lemah.
router.include_router(portal.router)

__all__ = ["router"]
