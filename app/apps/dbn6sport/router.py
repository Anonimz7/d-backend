"""Router gabungan dbn6sport. Mount di main.py dengan prefix /api/dbn6sport/v1."""
from __future__ import annotations

from fastapi import APIRouter

from .routers import (
    activity, auth, attendance, clients, corrections, dashboard, finance,
    members, messages, portal, programs, requests, schedule, settings, titip,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(members.router)
router.include_router(programs.router)
router.include_router(clients.router)
router.include_router(corrections.router)
router.include_router(schedule.router)
router.include_router(requests.router)
router.include_router(finance.router)
router.include_router(messages.router)
router.include_router(dashboard.router)
router.include_router(settings.router)
router.include_router(activity.router)
router.include_router(portal.router)
router.include_router(attendance.router)
router.include_router(titip.router)
