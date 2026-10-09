"""
Definisi bagian data (section) dan aturan aksesnya.

read_menus : menu yang butuh data ini untuk tampil (None = semua pengguna yang punya akses apa pun).
write_menu : key akses yang diperlukan untuk mengubah data ini.
"""
from dataclasses import dataclass

from .. import models, schemas


@dataclass(frozen=True)
class Section:
    name: str
    write_menu: str
    read_menus: frozenset[str] | None
    model: type | None = None
    schema: type | None = None
    pk: str = "id"
    ordered: bool = False  # True: urutan array klien disimpan di kolom position


SECTIONS: dict[str, Section] = {s.name: s for s in [
    Section("profile", "settings", None),
    Section("accounts", "accounts", frozenset({"accounts", "tx", "home", "report"}),
            models.Account, schemas.Account, ordered=True),
    Section("transactions", "tx", frozenset({"tx", "home", "report"}), models.Transaction, schemas.Transaction),
    Section("budgets", "budget", frozenset({"budget", "home", "report"}), models.Budget, schemas.Budget, pk="category"),
    Section("bills", "bills", frozenset({"bills", "home"}), models.Bill, schemas.Bill, ordered=True),
    Section("goals", "goals", frozenset({"goals", "home"}), models.Goal, schemas.Goal, ordered=True),
    Section("investments", "invest", frozenset({"invest", "home"}), models.Investment, schemas.Investment, ordered=True),
]}


def can_read(section: Section, keys: set[str]) -> bool:
    if section.read_menus is None:
        return bool(keys)
    return bool(section.read_menus & keys)


def can_write(section: Section, keys: set[str]) -> bool:
    return section.write_menu in keys
