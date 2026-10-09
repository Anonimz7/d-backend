"""Pabrik router CRUD: satu fungsi membangun endpoint standar untuk setiap Resource."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.claisrox.deps import require_menu
from app.apps.claisrox.resources import Resource
from app.core.database import get_db


def build_crud_router(res: Resource) -> APIRouter:
    schema, model = res.schema, res.model
    router = APIRouter(prefix=res.path, tags=[res.menu], dependencies=[Depends(require_menu(res.menu))])

    def get_or_404(db: Session, item_id: str):
        obj = db.get(model, item_id)
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Data tidak ditemukan")
        return obj

    @router.get("", response_model=list[schema])
    def list_items(db: Session = Depends(get_db)):
        return db.scalars(select(model)).all()

    @router.get("/{item_id}", response_model=schema)
    def read_item(item_id: str, db: Session = Depends(get_db)):
        return get_or_404(db, item_id)

    @router.post("", response_model=schema, status_code=status.HTTP_201_CREATED)
    def create_item(payload: schema, db: Session = Depends(get_db)):
        if db.get(model, payload.id) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "ID sudah dipakai")
        obj = model(**payload.model_dump())
        db.add(obj)
        db.commit()
        return obj

    @router.put("/{item_id}", response_model=schema)
    def update_item(item_id: str, payload: schema, db: Session = Depends(get_db)):
        obj = get_or_404(db, item_id)
        for field, value in payload.model_dump(exclude={"id"}).items():
            setattr(obj, field, value)
        db.commit()
        return obj

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_item(item_id: str, db: Session = Depends(get_db)):
        db.delete(get_or_404(db, item_id))
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
