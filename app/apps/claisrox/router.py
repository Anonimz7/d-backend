"""APIRouter gabungan claisrox — TANPA prefix global.

Di-mount dari main.py unified-backend dengan prefix="/api/claisrox",
sehingga path final = /api/claisrox/<path-relatif>.
Urutan include sama seperti main.py backend asli.
"""
from fastapi import APIRouter

from app.apps.claisrox.resources import RESOURCES
from app.apps.claisrox.routers import accounts, auth, finance, snapshot
from app.apps.claisrox.routers.crud import build_crud_router

router = APIRouter()

router.include_router(auth.router)
router.include_router(accounts.router)
router.include_router(snapshot.router)
router.include_router(finance.router)
for res in RESOURCES:
    router.include_router(build_crud_router(res))


@router.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
