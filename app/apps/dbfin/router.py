"""APIRouter gabungan DB Finance.

TANPA prefix global — mount point /api/dbfin di main.py yang menangani namespace.
Path relatif router dipertahankan apa adanya dari backend asli.
"""
from fastapi import APIRouter

from .routers import auth, state, accounts
from .routers.resources import routers as resource_routers

router = APIRouter()
router.include_router(auth.router)
router.include_router(accounts.router)
router.include_router(state.router)
for r in resource_routers:
    router.include_router(r)
