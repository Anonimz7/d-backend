"""Backend claisrox dalam unified-backend.

Namespace mount: /api/claisrox | schema PostgreSQL: clx | klaim token app="claisrox".
Di-mount dari main.py unified-backend: app.include_router(router, prefix="/api/claisrox")
"""
from app.apps.claisrox.router import router
from app.apps.claisrox.seed import ensure_owner

__all__ = ["router", "ensure_owner"]
