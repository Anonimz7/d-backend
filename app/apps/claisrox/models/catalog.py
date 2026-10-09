from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.apps.claisrox.models.types import Money
from app.core.database import app_base
Base = app_base("clx")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))
    buy_price: Mapped[float] = mapped_column(Money)
    sell_price: Mapped[float] = mapped_column(Money)
    stock: Mapped[float] = mapped_column(Float)
    min_stock: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20))


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = {"schema": "clx"}

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    unit: Mapped[str] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Money)
    stock: Mapped[float] = mapped_column(Float)
    min_stock: Mapped[float] = mapped_column(Float)
