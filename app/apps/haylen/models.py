"""Model tabel Haylen (schema PostgreSQL: haylen)."""
from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import JSONType, app_base  # noqa: F401 (JSONType: konvensi porting)
Base = app_base("haylen")

SCHEMA = "haylen"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="Owner")
    tier: Mapped[int] = mapped_column(Integer, default=0)  # 0=owner,1=admin,2=coach,3=reserved
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Member(Base):
    __tablename__ = "members"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(120))
    telepon: Mapped[str] = mapped_column(String(30), default="")
    program: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(20), default="Aktif")
    bergabung: Mapped[str] = mapped_column(String(10), default=lambda: date.today().isoformat())


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(80))
    kategori: Mapped[str] = mapped_column(String(40), default="")
    harga: Mapped[int] = mapped_column(BigInteger, default=0)
    kuota: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="Aktif")


class Coach(Base):
    __tablename__ = "coaches"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(120))
    telepon: Mapped[str] = mapped_column(String(30), default="")
    spesialisasi: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="Aktif")


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    kelas: Mapped[str] = mapped_column(String(80))
    coach: Mapped[str] = mapped_column(String(120), default="")
    hari: Mapped[str] = mapped_column(String(15), default="")
    jam: Mapped[str] = mapped_column(String(5), default="")
    kolam: Mapped[str] = mapped_column(String(60), default="")
    absensi: Mapped[str] = mapped_column(String(20), default="Belum")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    tanggal: Mapped[str] = mapped_column(String(10))
    member: Mapped[str] = mapped_column(String(120), default="-")
    keterangan: Mapped[str] = mapped_column(String(255), default="")
    jumlah: Mapped[int] = mapped_column(BigInteger, default=0)
    tipe: Mapped[str] = mapped_column(String(20), default="Pemasukan")  # Pemasukan | Pengeluaran


class Facility(Base):
    __tablename__ = "facilities"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(120))
    jenis: Mapped[str] = mapped_column(String(40), default="")
    kapasitas: Mapped[int] = mapped_column(Integer, default=0)
    kondisi: Mapped[str] = mapped_column(String(30), default="Baik")


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = {"schema": SCHEMA}
    id: Mapped[int] = mapped_column(primary_key=True)
    kunci: Mapped[str] = mapped_column(String(80), unique=True)
    nilai: Mapped[str] = mapped_column(String(255), default="")
