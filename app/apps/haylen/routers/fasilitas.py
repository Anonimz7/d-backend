from ..crud_factory import make_crud_router
from ..models import Facility

router = make_crud_router(Facility, menu="fasilitas", prefix="/facilities", tag="fasilitas")
