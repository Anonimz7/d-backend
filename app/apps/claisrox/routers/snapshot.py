"""Satu endpoint untuk seluruh data — dipakai frontend yang masih memegang state lengkap (DATA)."""
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.claisrox.access import can_access, can_read_all
from app.apps.claisrox.deps import get_current_user
from app.apps.claisrox.models import Finance, User
from app.apps.claisrox.resources import RESOURCES, Resource
from app.apps.claisrox.routers.finance import get_finance
from app.apps.claisrox.schemas.finance import FinanceSchema
from app.core.database import get_db

router = APIRouter(prefix="/snapshot", tags=["snapshot"])


def replace_collection(db: Session, res: Resource, items: list) -> None:
    incoming = {item.id: item for item in items}
    for row in db.scalars(select(res.model)).all():
        if row.id not in incoming:
            db.delete(row)
    for item in incoming.values():
        db.merge(res.model(**item.model_dump()))


@router.get("")
def read_snapshot(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    read_all = can_read_all(user.tier)
    data: dict[str, Any] = {}
    for res in RESOURCES:
        if read_all or can_access(user.tier, res.menu):
            rows = db.scalars(select(res.model)).all()
            data[res.key] = [res.schema.model_validate(r).model_dump(by_alias=True, mode="json") for r in rows]
    if read_all or can_access(user.tier, "keuangan"):
        data["finance"] = FinanceSchema.model_validate(get_finance(db)).model_dump(by_alias=True)
    db.commit()
    return data


@router.put("")
def write_snapshot(payload: dict[str, Any], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Menimpa koleksi yang boleh diubah tier ini; koleksi lain diabaikan."""
    saved = []
    for res in RESOURCES:
        if res.key in payload and can_access(user.tier, res.menu):
            items = TypeAdapter(list[res.schema]).validate_python(payload[res.key])
            replace_collection(db, res, items)
            saved.append(res.key)
    if "finance" in payload and can_access(user.tier, "keuangan"):
        finance = FinanceSchema.model_validate(payload["finance"])
        row = get_finance(db)
        for field, value in finance.model_dump().items():
            setattr(row, field, value)
        saved.append("finance")
    db.commit()
    return {"saved": saved}
