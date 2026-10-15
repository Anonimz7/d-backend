"""GET/POST /programs, PATCH /programs/{id}"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user

router = APIRouter()
_cnt = {"p": 100}


def _out(p):
    return {"id": p.id, "name": p.name, "price": p.price, "unit": p.unit,
            "wk": p.wk, "lvl": float(p.lvl), "peserta": p.peserta, "fee": p.fee}


@router.get("/programs")
def list_programs(user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return {"data": [_out(p) for p in db.query(models.Program).all()]}


@router.post("/programs", status_code=201)
def create_program(body: schemas.ProgramIn,
                   user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    _cnt["p"] += 1
    p = models.Program(id=f"p{_cnt['p']}", **body.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return {"data": _out(p)}


@router.patch("/programs/{pid}")
def patch_program(pid: str, body: schemas.ProgramPatch,
                  user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    p = db.query(models.Program).filter_by(id=pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program tidak ada")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit(); db.refresh(p)
    return {"data": _out(p)}
