"""Seed owner Haylen (dipanggil dari lifespan main.py)."""
from sqlalchemy.orm import Session

from app.core import security as core_security
from app.core.config import settings

from .models import User


def ensure_owner(db: Session) -> User:
    """Buat user owner (tier 0) bila belum ada; kembalikan user yang ada/dibuat."""
    user = db.query(User).filter(User.username == settings.HAYLEN_OWNER_USERNAME).first()
    if user:
        return user
    user = User(
        username=settings.HAYLEN_OWNER_USERNAME,
        password_hash=core_security.hash_password(settings.HAYLEN_OWNER_PASSWORD),
        name=settings.HAYLEN_OWNER_NAME,
        role="Owner",
        tier=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
