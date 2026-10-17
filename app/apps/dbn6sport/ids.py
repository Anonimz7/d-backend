"""Helper untuk generate ID unik yang tahan restart.

Menggantikan pola _cnt in-memory yang reset ke 100 setiap restart
dan menyebabkan duplicate key jika ID sudah ada di database.
"""
import re


def next_id(db, model, prefix, id_field="id", start=100):
    """Cari ID berikutnya yang belum dipakai: prefix + angka.

    Contoh: next_id(db, models.Member, "m") -> "m105" jika m104 sudah ada.
    """
    maxn = start
    col = getattr(model, id_field)
    for (eid,) in db.query(col).filter(col.like(prefix + "%")).all():
        m = re.match(re.escape(prefix) + r"(\d+)$", eid or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    return f"{prefix}{maxn + 1}"
