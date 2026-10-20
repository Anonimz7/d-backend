"""Model dbn6sport — backend untuk dash-n6sport. Skema PostgreSQL: dn6sport.

Desain: RANCANGAN_DBN6SPORT.md
- String ID sebagai PK (u1, cl1, p1, rp1, ...) — sama dengan frontend.
- Field fase-4 (note, grp, end, link_url, read_at) disimpan permanen.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer,
    Numeric, String, Text, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from app.core.database import app_base

Base = app_base("dn6sport")
SCHEMA = "dn6sport"


class Member(Base):
    __tablename__ = "members"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # u1
    name = Column(String(160), nullable=False)
    role = Column(String(16), nullable=False)  # owner|admin|head|coach
    login = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255))
    wa = Column(String(32))
    loc = Column(String(128))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # p1..p6
    name = Column(String(160), nullable=False)
    price = Column(Integer, nullable=False)
    unit = Column(String(32))
    wk = Column(Integer, nullable=False)
    lvl = Column(Numeric(4, 2), nullable=False)
    peserta = Column(Integer, nullable=False, default=1)
    fee = Column(Integer, nullable=False, default=0)
    detail = Column(JSONB, nullable=True)  # susunan program lengkap (sched, tpls, dll)


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # cl1
    uid = Column(String(16), unique=True, nullable=False, index=True)  # N6-1001
    name = Column(String(160), nullable=False, index=True)
    program_id = Column(String(16), ForeignKey(f"{SCHEMA}.programs.id"))
    start = Column(Date, nullable=False)
    end = Column(Date, nullable=True)
    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), index=True)
    cond = Column(String(64))
    renew = Column(Boolean, default=False)
    hrmax = Column(Integer)
    mp = Column(Integer)
    arch = Column(Date, nullable=True, index=True)
    note = Column(Text)
    grp = Column(String(16), nullable=True, index=True)
    share_url = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # rp1
    client_id = Column(String(16), ForeignKey(f"{SCHEMA}.clients.id", ondelete="CASCADE"),
                       nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    type = Column(String(32))
    plan_km = Column(Numeric(5, 1))
    km = Column(Numeric(5, 1))
    pace = Column(Integer)
    hr = Column(Integer)
    rasa = Column(Integer)
    note = Column(Text)
    missed = Column(Boolean, default=False)
    link_url = Column(Text, nullable=True)
    correction_by = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), nullable=True)
    correction_text = Column(Text, nullable=True)
    correction_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # t1
    date = Column(Date, nullable=False, index=True)
    type = Column(String(8), nullable=False, index=True)  # in|out
    category = Column(String(128))
    amount = Column(Integer, nullable=False)
    description = Column(Text)
    program_id = Column(String(16), ForeignKey(f"{SCHEMA}.programs.id"), nullable=True)
    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # r1
    type = Column(String(32), nullable=False)
    who = Column(String(16), nullable=False, index=True)
    date = Column(Date, nullable=True)
    date2 = Column(Date, nullable=True)
    detail = Column(Text)
    status = Column(String(16), default="Menunggu", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)
    kind = Column(String(16), nullable=False, index=True)  # team|dm|broadcast
    thread_id = Column(String(16), nullable=True, index=True)  # client_id utk DM
    sender = Column(String(16), nullable=False)
    to_text = Column(String(160), nullable=True)
    text = Column(Text, nullable=False)
    t = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)


class SchedulePattern(Base):
    __tablename__ = "schedule_patterns"
    __table_args__ = {"schema": SCHEMA}

    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), primary_key=True)
    day = Column(Integer, primary_key=True)  # 0=Senin..6=Minggu
    slots = Column(ARRAY(String), default=list)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # bk1
    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), index=True)
    client_id = Column(String(16), ForeignKey(f"{SCHEMA}.clients.id", ondelete="CASCADE"), index=True)
    day = Column(Integer)
    time = Column(String(8))


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(32), primary_key=True)  # date|coach|time
    date = Column(String(10), index=True)
    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), index=True)
    time = Column(String(8))
    status = Column(String(16))  # Hadir/Izin/Alpha
    by_name = Column(String(100))
    at = Column(String(8))


class CoachProfile(Base):
    __tablename__ = "coach_profiles"
    __table_args__ = {"schema": SCHEMA}

    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), primary_key=True)
    rating = Column(Float, default=4.5)
    reviews = Column(Integer, default=0)
    since = Column(String(10))
    skills = Column(JSONB, default=dict)  # {pub, ajar, ilmu, prog, kom}


class ShareLink(Base):
    __tablename__ = "share_links"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(32), primary_key=True)
    client_id = Column(String(16), ForeignKey(f"{SCHEMA}.clients.id", ondelete="CASCADE"), index=True)
    date = Column(String(10), index=True)
    url = Column(String(500))
    fix_text = Column(Text)
    fix_by = Column(String(16))
    fix_at = Column(DateTime)
    at = Column(DateTime, default=datetime.utcnow)


class CorrectionTemplate(Base):
    __tablename__ = "correction_templates"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(16), primary_key=True)  # t1
    title = Column(String(160))
    text = Column(Text, nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = {"schema": SCHEMA}

    key = Column(String(64), primary_key=True)  # targets|acl
    value = Column(JSONB, nullable=False)


class ActivityLog(Base):
    __tablename__ = "activity_log"
    __table_args__ = {"schema": SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    t = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    who = Column(String(160))
    text = Column(Text, nullable=False)


class CommissionPayment(Base):
    __tablename__ = "commission_payments"
    __table_args__ = {"schema": SCHEMA}

    id = Column(String(32), primary_key=True)
    coach_id = Column(String(16), ForeignKey(f"{SCHEMA}.members.id"), index=True)
    # F1 komisi per klien: pembayaran dicatat per klien. NULL = record legacy
    # era per-coach (tidak menandai klien mana pun; dimigrasikan di Fase 2).
    client_id = Column(String(16), ForeignKey(f"{SCHEMA}.clients.id"), nullable=True, index=True)
    period = Column(String(32))  # label periode, misal "7 hari"
    amount = Column(Integer, default=0)
    date = Column(String(10))
    method = Column(String(32))
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
