from app.apps.claisrox.schemas.base import CamelModel


class ProductSchema(CamelModel):
    id: str
    name: str
    category: str
    buy_price: float
    sell_price: float
    stock: float
    min_stock: float
    unit: str


class MaterialSchema(CamelModel):
    id: str
    name: str
    unit: str
    price: float
    stock: float
    min_stock: float
