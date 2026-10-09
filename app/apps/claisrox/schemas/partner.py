import datetime as dt

from app.apps.claisrox.schemas.base import CamelModel


class SupplierSchema(CamelModel):
    id: str
    name: str
    contact: str
    product: str
    status: str
    created_at: dt.date


class CustomerSchema(CamelModel):
    id: str
    name: str
    contact: str
    type: str
    created_at: dt.date
