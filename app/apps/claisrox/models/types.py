from sqlalchemy import Numeric

from app.core.database import JSONType as JsonType

# Uang dalam rupiah; asdecimal=False agar langsung float seperti di frontend.
Money = Numeric(16, 2, asdecimal=False)

__all__ = ["JsonType", "Money"]
