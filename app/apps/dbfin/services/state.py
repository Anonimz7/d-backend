"""Membaca dan menulis data pengguna per bagian (section). (porting DB Finance)

Upsert memakai ON CONFLICT dialek yang sesuai: PostgreSQL di produksi,
SQLite pada mode uji lokal (TEST_SQLITE). Semantik upsert+prune dipertahankan.
"""
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import models, schemas
from .sections import SECTIONS, Section, can_read, can_write

CHUNK = 500


def read_section(db: Session, user: models.User, section: Section):
    if section.name == "profile":
        return schemas.Profile(name=user.name, theme=user.theme, hide_balance=user.hide_balance)
    m = section.model
    stmt = select(m).where(m.user_id == user.id)
    if section.ordered:
        stmt = stmt.order_by(m.position)
    elif section.name == "transactions":
        stmt = stmt.order_by(m.ts, m.id)
    else:
        stmt = stmt.order_by(getattr(m, section.pk))
    return [section.schema.model_validate(r) for r in db.scalars(stmt)]


def read_state(db: Session, user: models.User, keys: set[str]) -> schemas.State:
    data = {name: read_section(db, user, s) for name, s in SECTIONS.items() if can_read(s, keys)}
    return schemas.State(**data)


def _rows(section: Section, user_id: int, items) -> list[dict]:
    rows = []
    for i, item in enumerate(items):
        row = item.model_dump()
        row["user_id"] = user_id
        if section.ordered:
            row["position"] = i
        rows.append(row)
    return rows


def _upsert(db: Session, section: Section, rows: list[dict]) -> None:
    m = section.model
    pk_cols = [c.name for c in m.__table__.primary_key.columns]
    dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        # Produksi = PostgreSQL. Cabang dialek dipertahankan agar ON CONFLICT
        # tetap dipakai di produksi (bukan fallback hapus+tulis yang rawan FK).
        from sqlalchemy.dialects.postgresql import insert as dialect_insert
    for start in range(0, len(rows), CHUNK):
        stmt = dialect_insert(m).values(rows[start:start + CHUNK])
        update = {c.name: stmt.excluded[c.name] for c in m.__table__.columns if c.name not in pk_cols}
        db.execute(stmt.on_conflict_do_update(index_elements=pk_cols, set_=update))


def _prune(db: Session, section: Section, user_id: int, keep: list) -> None:
    m = section.model
    col = getattr(m, section.pk)
    stmt = delete(m).where(m.user_id == user_id)
    if keep:
        stmt = stmt.where(col.not_in(keep))
    db.execute(stmt)


def write_state(db: Session, user: models.User, doc: schemas.State, keys: set[str]) -> None:
    """
    Menimpa bagian yang dikirim dan boleh ditulis oleh tier pengguna; bagian lain dibiarkan.
    Urutan menjaga foreign key: rekening masuk dulu, transaksi, lalu hapus yang tidak lagi ada.
    """
    sections = {name: s for name, s in SECTIONS.items() if getattr(doc, name) is not None and can_write(s, keys)}

    if "profile" in sections:
        p = doc.profile
        user.name, user.theme, user.hide_balance = p.name, p.theme, p.hide_balance

    prepared = {n: _rows(s, user.id, getattr(doc, n)) for n, s in sections.items() if s.model}
    for name in ("accounts", "transactions", "budgets", "bills", "goals", "investments"):
        if name in prepared:
            _upsert(db, sections[name], prepared[name])
    for name in ("transactions", "accounts", "budgets", "bills", "goals", "investments"):
        if name in prepared:
            s = sections[name]
            _prune(db, s, user.id, [r[s.pk] for r in prepared[name]])
