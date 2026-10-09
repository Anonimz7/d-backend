"""Dependency auth claisrox: Bearer JWT (klaim app="claisrox") + user dari DB.

Berbeda dari backend asli: token memakai klaim app/tier/typ dari
app.core.security (bcrypt + JWT HS256), dan user dimuat by id (sub)
dengan tier diambil dari baris DB — bukan dari token.
"""
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.apps.claisrox.access import can_access
from app.apps.claisrox.models import User
from app.core import security
from app.core.database import get_db

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    user: User | None = None
    if credentials:
        try:
            payload = security.decode_token(credentials.credentials, app="claisrox")
        except security.TokenError:
            payload = None
        else:
            try:
                user_id = int(payload["sub"])
            except (KeyError, TypeError, ValueError):
                user_id = None
            if user_id is not None:
                user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesi tidak valid")
    return user


def require_menu(menu: str) -> Callable[[User], User]:
    def checker(user: User = Depends(get_current_user)) -> User:
        if not can_access(user.tier, menu):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Tier {user.tier} tidak punya akses ke '{menu}'")
        return user

    return checker
