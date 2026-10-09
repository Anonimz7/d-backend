"""User aktif Haylen dari Bearer JWT terpadu.

Token dibuat via app.core.security dengan klaim app="haylen".
User dimuat dari DB (schema haylen); tier diambil dari kolom DB,
bukan dari klaim token.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security as core_security
from app.core.database import get_db

from .models import User

bearer = HTTPBearer(auto_error=False)
APP_CLAIM = "haylen"


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Belum login")
    try:
        data = core_security.decode_token(cred.credentials, app=APP_CLAIM)
    except core_security.TokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak valid")
    try:
        user_id = int(data["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak valid")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User tidak ditemukan")
    return user
