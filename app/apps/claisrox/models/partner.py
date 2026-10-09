import datetime as dt

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import app_base
Base = app_base("clx")


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    contact: Mapped[str] = mapped_column(String(50))
    product: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[dt.date] = mapped_column(Date)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    contact: Mapped[str] = mapped_column(String(50))
    type: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[dt.date] = mapped_column(Date)
