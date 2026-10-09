import datetime as dt

from sqlalchemy import Date, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.apps.claisrox.models.types import JsonType, Money
from app.core.database import app_base
Base = app_base("clx")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    customer_id: Mapped[str] = mapped_column(String(32))
    items: Mapped[list] = mapped_column(JsonType)          # [{product_id, qty, price}]
    total: Mapped[float] = mapped_column(Money)


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    supplier_id: Mapped[str] = mapped_column(String(32))
    items: Mapped[list] = mapped_column(JsonType)          # [{material_id, qty, price}]
    total: Mapped[float] = mapped_column(Money)


class OnlineOrder(Base):
    __tablename__ = "online_orders"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    resi: Mapped[str] = mapped_column(String(40), unique=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    customer_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(50))
    address: Mapped[str] = mapped_column(Text)
    items: Mapped[list] = mapped_column(JsonType)          # [{product_id, qty, price}]
    total: Mapped[float] = mapped_column(Money)
    status: Mapped[str] = mapped_column(String(20))
