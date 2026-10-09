"""Security terpadu: bcrypt + JWT HS256 untuk kelima aplikasi.

Klaim token:
    sub  : id user (string)
    app  : namespace aplikasi ("haylen" | "n6" | "dbacc" | "dbfin" | "claisrox")
    tier : tier user (int)
    typ  : "access" | "refresh"
    iat / exp

CATATAN MIGRASI: backend-backend lama memakai PBKDF2 (Haylen), scrypt
(DB Finance, claisrox), dan SHA-256 stub (DB Accounting). Hash lama TIDAK
dapat diverifikasi oleh modul ini — user lama harus dibuat ulang
(owner dibuat otomatis dari .env saat startup).
"""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings


def hash_password(password: str) -> str:
    if len(password.encode()) > 72:
        raise ValueError("Password maksimal 72 byte")
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, app: str, sub: str, tier: int) -> str:
    payload = {
        "sub": str(sub),
        "app": app,
        "tier": int(tier),
        "typ": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(*, app: str, sub: str) -> str:
    payload = {
        "sub": str(sub),
        "app": app,
        "typ": "refresh",
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class TokenError(ValueError):
    pass


def decode_token(token: str, *, app: str, expect_typ: str = "access") -> dict:
    """Decode + validasi; raise TokenError bila tidak valid / bukan milik app ini."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise TokenError("Token kedaluwarsa") from e
    except jwt.PyJWTError as e:
        raise TokenError("Token tidak valid") from e
    if payload.get("typ", "access") != expect_typ:
        raise TokenError("Tipe token salah")
    if payload.get("app") != app:
        raise TokenError("Token bukan untuk aplikasi ini")
    return payload
