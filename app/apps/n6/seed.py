from __future__ import annotations
"""Seed N6 untuk unified-backend. Porting dari N6/backend/app/seed.py.

Hanya menyediakan ensure_owner(db): membuat akun owner tier 0 dari
N6_OWNER_USERNAME / N6_OWNER_PASSWORD / N6_OWNER_NAME bila username masih
bebas. Aman dijalankan ulang. Akun admin opsional dari seed asli SENGAJA
dilewati (sesuai spesifikasi porting).

Dipanggil dari main.py unified-backend saat startup (setelah init_db()).
Tidak membuat tabel di sini — itu tugas app.core.database.init_db().
"""


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings

from .models import Account
from .tiers import TIER_OWNER


def ensure_owner(db: Session) -> bool:
    """Buat owner N6 bila belum ada. Return True bila dibuat."""
    username = settings.N6_OWNER_USERNAME
    existing = db.scalar(select(Account).where(Account.username == username))
    if existing is not None:
        return False
    db.add(
        Account(
            username=username,
            full_name=settings.N6_OWNER_NAME,
            password_hash=security.hash_password(settings.N6_OWNER_PASSWORD),
            tier=TIER_OWNER,
            is_active=True,
        )
    )
    db.commit()
    return True
