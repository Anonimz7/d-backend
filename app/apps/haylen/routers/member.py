from ..crud_factory import make_crud_router
from ..models import Member

router = make_crud_router(Member, menu="member", prefix="/members", tag="member")
