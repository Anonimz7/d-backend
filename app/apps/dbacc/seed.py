"""Seed owner DB Accounting — dipanggil dari lifespan main.py."""
import uuid

from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings

from . import models


def ensure_owner(db: Session) -> None:
    """Buat user owner (tier 0) dari env bila belum ada user dengan email itu."""
    email = settings.DBACC_OWNER_EMAIL.strip().lower()
    exists = db.query(models.User).filter(models.User.email == email).first()
    if exists:
        return
    db.add(
        models.User(
            id=str(uuid.uuid4()),
            name=settings.DBACC_OWNER_NAME,
            email=email,
            password_hash=security.hash_password(settings.DBACC_OWNER_PASSWORD),
            tier=0,
        )
    )
    db.commit()
