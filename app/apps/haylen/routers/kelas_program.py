from ..crud_factory import make_crud_router
from ..models import Program

router = make_crud_router(Program, menu="kelas_program", prefix="/programs", tag="kelas & program")
