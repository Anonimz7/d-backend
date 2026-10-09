"""APIRouter gabungan DB Accounting.

TANPA prefix global — mount point di main.py yang menangani namespace
(/api/dbacc). Path relatif tiap router dipertahankan seperti aslinya.
"""
from fastapi import APIRouter

from .routers import accounts, auth, companies, reports, transactions

router = APIRouter()
router.include_router(auth.router)
router.include_router(accounts.router)
router.include_router(companies.router)
router.include_router(transactions.router)
router.include_router(reports.router)
