"""Model DB Accounting (schema: daccounting).

Migrasi dari JSON payload ke tabel relasional (2026-10-10).
"""
import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func

from app.core.database import app_base
Base = app_base("daccounting")


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    tier = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True)
    owner_id = Column(String, index=True, nullable=True)
    name = Column(String, nullable=False)
    industry = Column(String, default="")
    color = Column(String, default="#1EB682")
    initial = Column(String, default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CoaAccount(Base):
    """Chart of Accounts per perusahaan."""
    __tablename__ = "coa_accounts"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # Aset|Kewajiban|Modal|Pendapatan|Beban
    normal = Column(String(6), nullable=False, default="debit")  # debit|credit
    is_active = Column(Boolean, nullable=False, default=True)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), default="")
    phone = Column(String(50), default="")
    address = Column(String(255), default="")


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(150), default="")
    phone = Column(String(50), default="")
    address = Column(String(255), default="")


class Journal(Base):
    """Header jurnal double-entry."""
    __tablename__ = "journals"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    description = Column(String(255), default="")
    ref_no = Column(String(50), default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    journal_id = Column(String, ForeignKey("daccounting.journals.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("daccounting.coa_accounts.id"), nullable=False, index=True)
    debit = Column(Numeric(18, 2), nullable=False, default=0)
    credit = Column(Numeric(18, 2), nullable=False, default=0)


class SalesInvoice(Base):
    __tablename__ = "sales_invoices"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    invoice_no = Column(String(50), nullable=False)
    customer_id = Column(String, ForeignKey("daccounting.customers.id"), nullable=True)
    date = Column(Date, nullable=False, index=True)
    total = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SalesInvoiceLine(Base):
    __tablename__ = "sales_invoice_lines"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    invoice_id = Column(String, ForeignKey("daccounting.sales_invoices.id"), nullable=False, index=True)
    description = Column(String(255), default="")
    qty = Column(Numeric(18, 2), default=1)
    price = Column(Numeric(18, 2), default=0)
    subtotal = Column(Numeric(18, 2), default=0)


class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    invoice_no = Column(String(50), nullable=False)
    supplier_id = Column(String, ForeignKey("daccounting.suppliers.id"), nullable=True)
    date = Column(Date, nullable=False, index=True)
    total = Column(Numeric(18, 2), nullable=False, default=0)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PurchaseInvoiceLine(Base):
    __tablename__ = "purchase_invoice_lines"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    invoice_id = Column(String, ForeignKey("daccounting.purchase_invoices.id"), nullable=False, index=True)
    description = Column(String(255), default="")
    qty = Column(Numeric(18, 2), default=1)
    price = Column(Numeric(18, 2), default=0)
    subtotal = Column(Numeric(18, 2), default=0)


class CashBankTransaction(Base):
    __tablename__ = "cashbank_transactions"
    __table_args__ = {"schema": "daccounting"}

    id = Column(String, primary_key=True, default=_uuid)
    company_id = Column(String, ForeignKey("daccounting.companies.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # masuk|keluar
    account_id = Column(String, ForeignKey("daccounting.coa_accounts.id"), nullable=False, index=True)
    amount = Column(Numeric(18, 2), nullable=False, default=0)
    description = Column(String(255), default="")
    ref_no = Column(String(50), default="")
