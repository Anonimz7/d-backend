"""
Satu pasang endpoint GET/PUT per menu (mis. /transactions untuk menu `tx`).
Dibuat dari SECTIONS supaya aturan akses tidak ditulis ulang di tiap file.
(porting DB Finance — path absolut tanpa prefix dipertahankan apa adanya;
mount /api/dbfin yang menangani namespace.)
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..deps import access_keys, current_user, require_menu
from ..services.sections import SECTIONS, can_read
from ..services.state import read_section, write_state

PATHS = {
    "profile": "/profile",
    "accounts": "/accounts",
    "transactions": "/transactions",
    "budgets": "/budgets",
    "bills": "/bills",
    "goals": "/goals",
    "investments": "/investments",
}


def _build(name: str) -> APIRouter:
    section = SECTIONS[name]
    r = APIRouter(prefix=PATHS[name], tags=[name])
    body_type = section.schema if section.name != "profile" else schemas.Profile
    response_type = body_type if section.name == "profile" else list[body_type]

    @r.get("", response_model=response_type)
    def list_items(user: models.User = Depends(current_user), keys: set[str] = Depends(access_keys),
                   db: Session = Depends(get_db)):
        if not can_read(section, keys):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Tier Anda tidak memiliki akses ke fitur ini")
        return read_section(db, user, section)

    @r.put("", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_menu(section.write_menu))])
    def replace_items(payload: response_type, user: models.User = Depends(current_user),
                      keys: set[str] = Depends(access_keys), db: Session = Depends(get_db)):
        try:
            write_state(db, user, schemas.State(**{name: payload}), keys)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "Data merujuk ke rekening yang tidak ada atau masih dipakai transaksi")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return r


routers = [_build(n) for n in PATHS]
