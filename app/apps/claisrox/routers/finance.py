from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.apps.claisrox.deps import require_menu
from app.apps.claisrox.models import Finance
from app.apps.claisrox.models.finance import FINANCE_ROW_ID
from app.apps.claisrox.schemas.finance import FinanceSchema
from app.core.database import get_db

router = APIRouter(prefix="/keuangan", tags=["keuangan"], dependencies=[Depends(require_menu("keuangan"))])


def get_finance(db: Session) -> Finance:
    row = db.get(Finance, FINANCE_ROW_ID)
    if row is None:
        row = Finance(id=FINANCE_ROW_ID, modal=0, piutang=0, hutang=0)
        db.add(row)
        db.flush()
    return row


@router.get("", response_model=FinanceSchema)
def read_finance(db: Session = Depends(get_db)):
    return get_finance(db)


@router.put("", response_model=FinanceSchema)
def update_finance(payload: FinanceSchema, db: Session = Depends(get_db)):
    row = get_finance(db)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.commit()
    return row
