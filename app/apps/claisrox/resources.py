"""Registri koleksi data. Satu baris per menu sidebar yang punya data.

`key` sama dengan nama properti di frontend (DATA.products, DATA.sales, ...),
`menu` adalah kunci akses di file tier JSON.
"""
from dataclasses import dataclass

from app.apps.claisrox.models import Customer, Material, OnlineOrder, Product, Production, Purchase, Recipe, Sale, Supplier
from app.apps.claisrox.schemas.catalog import MaterialSchema, ProductSchema
from app.apps.claisrox.schemas.partner import CustomerSchema, SupplierSchema
from app.apps.claisrox.schemas.production import ProductionSchema, RecipeSchema
from app.apps.claisrox.schemas.transaction import OnlineOrderSchema, PurchaseSchema, SaleSchema


@dataclass(frozen=True)
class Resource:
    key: str
    path: str
    menu: str
    model: type
    schema: type


RESOURCES = [
    Resource("products", "/produk", "produk", Product, ProductSchema),
    Resource("materials", "/bahan-baku", "bahan-baku", Material, MaterialSchema),
    Resource("suppliers", "/supplier", "supplier", Supplier, SupplierSchema),
    Resource("customers", "/customer", "customer", Customer, CustomerSchema),
    Resource("sales", "/penjualan", "penjualan", Sale, SaleSchema),
    Resource("purchases", "/pembelian", "pembelian", Purchase, PurchaseSchema),
    Resource("recipes", "/resep", "resep", Recipe, RecipeSchema),
    Resource("productions", "/produksi", "produksi", Production, ProductionSchema),
    Resource("onlineOrders", "/online", "online", OnlineOrder, OnlineOrderSchema),
]
