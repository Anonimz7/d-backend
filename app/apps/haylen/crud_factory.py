"""Pembuat router CRUD generik yang dijaga oleh akses tier."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from .access import require_menu


def to_dict(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def make_crud_router(model, menu: str, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])
    columns = {c.name for c in model.__table__.columns if c.name != "id"}

    def clean(body: dict) -> dict:
        return {k: v for k, v in body.items() if k in columns}

    @router.get("", dependencies=[Depends(require_menu(menu, "GET"))])
    def list_items(db: Session = Depends(get_db)):
        return [to_dict(o) for o in db.query(model).order_by(model.id).all()]

    @router.post("", status_code=201, dependencies=[Depends(require_menu(menu, "POST"))])
    def create_item(body: dict, db: Session = Depends(get_db)):
        obj = model(**clean(body))
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return to_dict(obj)

    @router.put("/{item_id}", dependencies=[Depends(require_menu(menu, "PUT"))])
    def update_item(item_id: int, body: dict, db: Session = Depends(get_db)):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, "Data tidak ditemukan")
        for k, v in clean(body).items():
            setattr(obj, k, v)
        db.commit()
        db.refresh(obj)
        return to_dict(obj)

    @router.delete("/{item_id}", status_code=204, dependencies=[Depends(require_menu(menu, "DELETE"))])
    def delete_item(item_id: int, db: Session = Depends(get_db)):
        obj = db.get(model, item_id)
        if not obj:
            raise HTTPException(404, "Data tidak ditemukan")
        db.delete(obj)
        db.commit()

    return router
