import datetime as dt

from app.apps.claisrox.schemas.base import CamelModel


class ProductLine(CamelModel):
    product_id: str
    qty: float
    price: float


class MaterialLine(CamelModel):
    material_id: str
    qty: float
    price: float


class SaleSchema(CamelModel):
    id: str
    code: str
    date: dt.date
    customer_id: str
    items: list[ProductLine]
    total: float


class PurchaseSchema(CamelModel):
    id: str
    code: str
    date: dt.date
    supplier_id: str
    items: list[MaterialLine]
    total: float


class OnlineOrderSchema(CamelModel):
    id: str
    resi: str
    date: dt.date
    customer_name: str
    phone: str
    address: str
    items: list[ProductLine]
    total: float
    status: str
