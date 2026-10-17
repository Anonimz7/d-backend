"""GET/POST /programs, PATCH /programs/{id}"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..access import get_current_user
from ..ids import next_id

router = APIRouter()


def _out(p):
    return {"id": p.id, "name": p.name, "price": p.price, "unit": p.unit,
            "wk": p.wk, "lvl": float(p.lvl), "peserta": p.peserta, "fee": p.fee,
            "detail": p.detail}


@router.get("/programs")
def list_programs(user: models.Member = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    return {"data": [_out(p) for p in db.query(models.Program).all()]}


@router.post("/programs", status_code=201)
def create_program(body: schemas.ProgramIn,
                   user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = models.Program(id=next_id(db, models.Program, "p"), **body.model_dump())
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


@router.delete("/programs/{pid}", status_code=204)
def delete_program(pid: str, user: models.Member = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    p = db.query(models.Program).filter_by(id=pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program tidak ada")
    n = db.query(models.Client).filter_by(program_id=pid).count()
    if n:
        raise HTTPException(status_code=400, detail=f"Masih dipakai {n} klien.")
    db.delete(p)
    db.commit()
    return None
