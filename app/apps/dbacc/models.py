"""Model DB Accounting (schema: dbacc).

Salinan dari DB Acounting/backend/app/models.py dengan adaptasi:
- Base & JSONType dari app.core.database
- __table_args__ schema "dbacc"
- Kolom/tabel tidak berubah.
"""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.core.database import JSONType, app_base
Base = app_base("dbacc")


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "dbacc"}

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tier = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": "dbacc"}

    id = Column(String, primary_key=True)
    owner_id = Column(String, index=True, nullable=True)
    name = Column(String, nullable=False)
    industry = Column(String, default="")
    color = Column(String, default="#1EB682")
    initial = Column(String, default="")
    payload = Column(JSONType, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
