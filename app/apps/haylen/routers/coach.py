from ..crud_factory import make_crud_router
from ..models import Coach

router = make_crud_router(Coach, menu="coach", prefix="/coaches", tag="coach")
