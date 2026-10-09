"""Seed claisrox: pastikan satu akun owner (tier 0) ada.

Dipanggil dari lifespan main.py unified-backend, setelah init_db().
Kredensial dari env: CLX_OWNER_USERNAME / CLX_OWNER_PASSWORD / CLX_OWNER_NAME.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.claisrox.models import User
from app.core import security
from app.core.config import settings


def ensure_owner(db: Session) -> User:
    user = db.scalar(select(User).where(User.username == settings.CLX_OWNER_USERNAME))
    if user is None:
        user = User(
            username=settings.CLX_OWNER_USERNAME,
            password_hash=security.hash_password(settings.CLX_OWNER_PASSWORD),
            name=settings.CLX_OWNER_NAME,
            tier=0,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
