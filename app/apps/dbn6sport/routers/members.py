"""GET/POST /members, PATCH /members/{id}"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user

router = APIRouter()
_cnt = {"m": 100}


def _nid(p):
    _cnt[p] += 1
    return f"{p}{_cnt[p]}"


def _out(m):
    return {"id": m.id, "name": m.name, "role": m.role, "login": m.login,
            "email": m.email, "wa": m.wa, "loc": m.loc}


@router.get("/members")
def list_members(user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    return {"data": [_out(m) for m in db.query(models.Member).all()]}


@router.post("/members", status_code=201)
def create_member(body: schemas.MemberIn,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    m = models.Member(id=_nid("m"), name=body.name, role=body.role,
                      login=body.login, email=body.email, wa=body.wa or "",
                      loc=body.loc or "",
                      password_hash=bcrypt.hashpw(b"x", bcrypt.gensalt()).decode())
    db.add(m); db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.patch("/members/{mid}")
def patch_member(mid: str, body: schemas.MemberPatch,
                 user: models.Member = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    m = db.query(models.Member).filter_by(id=mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="Anggota tidak ada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit(); db.refresh(m)
    return {"data": _out(m)}


@router.delete("/members/{mid}", status_code=204)
def delete_member(mid: str,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    m = db.query(models.Member).filter_by(id=mid).first()
    if not m:
        raise HTTPException(status_code=404, detail="Anggota tidak ada")
    if m.id == user.id:
        raise HTTPException(status_code=400, detail="Tidak bisa hapus akun sendiri")
    if m.role == "owner":
        raise HTTPException(status_code=400, detail="Tidak bisa hapus owner")
    db.delete(m)
    db.commit()
    return None
