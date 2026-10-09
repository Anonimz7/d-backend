import datetime as dt

from app.apps.claisrox.schemas.base import CamelModel


class Ingredient(CamelModel):
    material_id: str
    percent: float


class RecipeSchema(CamelModel):
    id: str
    name: str
    output_product_id: str
    batch_size: float
    batch_unit: str
    fill_per_unit: float
    packaging_material_id: str | None = None
    packaging_qty_per_unit: float = 0
    labor_cost: float = 0
    overhead_cost: float = 0
    ingredients: list[Ingredient]


class ProductionSchema(CamelModel):
    id: str
    code: str
    date: dt.date
    recipe_id: str
    batches: float
    produced_qty: float
    total_cost: float
    cost_per_unit: float
