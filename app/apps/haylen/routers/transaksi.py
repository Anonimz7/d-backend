from ..crud_factory import make_crud_router
from ..models import Transaction

router = make_crud_router(Transaction, menu="transaksi", prefix="/transactions", tag="transaksi")
