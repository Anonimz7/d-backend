"""POST /auth/login, GET /auth/me"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db

from .. import models, schemas
from ..access import APP_CLAIM, get_current_user

router = APIRouter()


def _out(m: models.Member) -> dict:
    return {"id": m.id, "name": m.name, "role": m.role, "login": m.login,
            "email": m.email, "wa": m.wa, "loc": m.loc}


@router.post("/auth/login")
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    m = db.query(models.Member).filter(models.Member.login == body.login_id).first()
    if not m:
        raise HTTPException(status_code=401, detail="Login tidak ditemukan")
    if not security.verify_password(body.password or "", m.password_hash):
        raise HTTPException(status_code=401, detail="Password salah")
    token = security.create_access_token(app=APP_CLAIM, sub=m.id, tier=0)
    return {"token": token, "user": _out(m)}


@router.get("/auth/me")
def me(user: models.Member = Depends(get_current_user)):
    return {"user": _out(user)}
