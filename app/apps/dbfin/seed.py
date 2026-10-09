"""Seed owner DB Finance. Dipanggil dari main.py unified-backend saat startup.

Membuat user owner (tier 0) dari DBFIN_OWNER_USERNAME/PASSWORD/NAME bila belum ada.
Password di-hash dengan bcrypt (app.core.security); hash scrypt lama tidak didukung.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings

from . import models


def ensure_owner(db: Session) -> None:
    if db.scalar(select(models.User).where(models.User.username == settings.DBFIN_OWNER_USERNAME)):
        return
    db.add(models.User(
        username=settings.DBFIN_OWNER_USERNAME,
        password_hash=security.hash_password(settings.DBFIN_OWNER_PASSWORD),
        name=settings.DBFIN_OWNER_NAME,
        tier=0,
    ))
    db.commit()
