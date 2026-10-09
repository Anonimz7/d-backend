from ..crud_factory import make_crud_router
from ..models import Setting

router = make_crud_router(Setting, menu="pengaturan", prefix="/settings", tag="pengaturan")
