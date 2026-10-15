"""Auth dbn6sport via JWT (klaim app="dbn6sport")."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db

from . import models

bearer_scheme = HTTPBearer(auto_error=False)
APP_CLAIM = "dbn6sport"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.Member:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token tidak ditemukan",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = security.decode_token(credentials.credentials, app=APP_CLAIM)
    except security.TokenError as e:
        raise HTTPException(status_code=401, detail=str(e),
                            headers={"WWW-Authenticate": "Bearer"}) from e
    user = db.query(models.Member).filter(models.Member.id == str(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require_role(*roles: str):
    def guard(user: models.Member = Depends(get_current_user)) -> models.Member:
        if user.role not in roles and user.role != "owner":
            raise HTTPException(status_code=403, detail="Akses ditolak")
        return user
    return guard
