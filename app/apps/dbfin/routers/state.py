from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db

from .. import models, schemas
from ..deps import access_keys, current_user
from ..services.state import read_state, write_state

router = APIRouter(tags=["state"])


@router.get("/state", response_model=schemas.State, response_model_exclude_unset=True)
def get_state(user: models.User = Depends(current_user), keys: set[str] = Depends(access_keys),
              db: Session = Depends(get_db)):
    return read_state(db, user, keys)


@router.put("/state", status_code=status.HTTP_204_NO_CONTENT)
def put_state(doc: schemas.State, user: models.User = Depends(current_user),
              keys: set[str] = Depends(access_keys), db: Session = Depends(get_db)):
    try:
        write_state(db, user, doc, keys)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Data merujuk ke rekening yang tidak ada atau masih dipakai transaksi")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
