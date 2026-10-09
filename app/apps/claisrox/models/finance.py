from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.apps.claisrox.models.types import Money
from app.core.database import app_base
Base = app_base("clx")

FINANCE_ROW_ID = 1


class Finance(Base):
    """Satu baris saja: modal, piutang, hutang."""

    __tablename__ = "finance"
    __table_args__ = {"schema": "clx"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=FINANCE_ROW_ID)
    modal: Mapped[float] = mapped_column(Money, default=0)
    piutang: Mapped[float] = mapped_column(Money, default=0)
    hutang: Mapped[float] = mapped_column(Money, default=0)
