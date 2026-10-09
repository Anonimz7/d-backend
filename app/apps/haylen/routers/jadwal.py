from ..crud_factory import make_crud_router
from ..models import Schedule

router = make_crud_router(Schedule, menu="jadwal", prefix="/schedules", tag="jadwal")
