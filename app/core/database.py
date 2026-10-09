"""Database bersama: satu database PostgreSQL, satu schema per aplikasi.

Schema: haylen | n6 | dbacc | dbfin | clx
Semua model aplikasi memakai Base ini dan wajib mencantumkan
__table_args__ = {"schema": "<nama-schema>"}.

Mode TEST_SQLITE: bila DATABASE_URL diawali "sqlite", schema di-ATTACH
sebagai database :memory: terpisah. Hanya untuk pengujian lokal —
produksi memakai PostgreSQL.
"""
from sqlalchemy import JSON as SAJSON, MetaData, create_engine, event, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

# JSON portabel: JSONB di PostgreSQL, JSON biasa di tempat lain (mis. uji SQLite)
JSONType = SAJSON().with_variant(postgresql.JSONB(), "postgresql")

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

APP_SCHEMAS = ["haylen", "n6", "dbacc", "dbfin", "clx"]

_BASES: dict = {}


def app_base(name: str):
    """Dedicated declarative base per aplikasi (registry class terisolasi).

    Dipakai karena nama class model bertabrakan antar aplikasi
    (mis. `User`, `Account`, `Transaction` ada di beberapa aplikasi).
    """
    if name not in _BASES:
        _BASES[name] = declarative_base(metadata=MetaData(naming_convention=NAMING_CONVENTION))
    return _BASES[name]

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    **({} if IS_SQLITE else {}),
)


def _attach_sqlite_schemas(dbapi_conn, _):
    """Uji lokal: tiap schema = database :memory: tersendiri."""
    cur = dbapi_conn.cursor()
    for schema in APP_SCHEMAS:
        cur.execute(f'ATTACH DATABASE \':memory:\' AS "{schema}"')
    cur.close()


if IS_SQLITE:
    event.listen(engine, "connect", _attach_sqlite_schemas)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Buat schema (PostgreSQL) + semua tabel dari semua aplikasi."""
    if not IS_SQLITE:
        with engine.begin() as conn:
            for schema in APP_SCHEMAS:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    for base in _BASES.values():
        base.metadata.create_all(engine)


def get_db():
    """Dependency FastAPI: sesi DB per-request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
