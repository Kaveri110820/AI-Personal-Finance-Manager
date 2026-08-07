"""SQLAlchemy ORM models for the personal finance manager.

Tables: transactions, budgets, bills, investments, users, reports, history.
All tables are created automatically on init_db() if missing.
"""

import datetime as dt
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="Others")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = (
        Index("idx_transactions_date", "date"),
        Index("idx_transactions_category", "category"),
        UniqueConstraint("date", "description", "amount", name="idx_transactions_fingerprint"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "category": self.category,
            "amount": self.amount,
            "balance": self.balance,
            "source": self.source,
            "created_at": self.created_at,
        }


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = (
        CheckConstraint("scope IN ('monthly', 'category')", name="ck_budgets_scope"),
        CheckConstraint(
            "(scope = 'monthly' AND category IS NULL) "
            "OR (scope = 'category' AND category IS NOT NULL)",
            name="ck_budgets_scope_category",
        ),
        CheckConstraint("amount >= 0", name="ck_budgets_amount"),
        Index(
            "idx_budgets_monthly",
            "scope",
            unique=True,
            sqlite_where=text("category IS NULL"),
        ),
        Index(
            "idx_budgets_category",
            "scope",
            "category",
            unique=True,
            sqlite_where=text("category IS NOT NULL"),
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scope": self.scope,
            "category": self.category,
            "amount": self.amount,
        }


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'paid')", name="ck_bills_status"),
        CheckConstraint("amount >= 0", name="ck_bills_amount"),
        Index("idx_bills_due_date", "due_date"),
        Index("idx_bills_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "due_date": self.due_date,
            "amount": self.amount,
            "status": self.status,
        }


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    investment_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_investments_amount"),
        Index("idx_investments_type", "investment_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "investment_type": self.investment_type,
            "amount": self.amount,
        }


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(collation="NOCASE"), nullable=False, unique=True
    )
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = ()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at,
        }


class Report(Base):
    """One snapshot row per generated monthly report."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    income: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expense: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    savings: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    savings_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    budget_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bills_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bills_paid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bills_pending: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    investment_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    categories_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget_overview_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    allocation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = (
        UniqueConstraint("year", "month", "user_id", name="uq_reports_month_user"),
        Index("idx_reports_created", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "year": self.year,
            "month": self.month,
            "income": self.income,
            "expense": self.expense,
            "savings": self.savings,
            "savings_rate": self.savings_rate,
            "budget_total": self.budget_total,
            "bills_total": self.bills_total,
            "bills_paid": self.bills_paid,
            "bills_pending": self.bills_pending,
            "investment_total": self.investment_total,
            "categories_json": self.categories_json,
            "budget_overview_json": self.budget_overview_json,
            "bills_json": self.bills_json,
            "allocation_json": self.allocation_json,
            "summary_json": self.summary_json,
            "created_at": self.created_at,
        }


class History(Base):
    """Audit log of user actions across all entities."""

    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)

    __table_args__ = (
        Index("idx_history_entity", "entity_type", "entity_id"),
        Index("idx_history_created", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": self.details,
            "created_at": self.created_at,
        }
