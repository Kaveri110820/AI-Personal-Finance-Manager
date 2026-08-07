"""Reusable CRUD repositories for the SQLAlchemy ORM models.

BaseCRUDRepository provides generic create / read / update / delete operations.
Specialised repositories add domain-specific helpers (e.g. deduplication for
transactions, monthly report upserts).
"""

import json
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update as sa_update
from sqlalchemy.orm import Session

from database.models import (
    Base,
    Bill,
    Budget,
    History,
    Investment,
    Report,
    Transaction,
    User,
)

M = TypeVar("M", bound=Base)


class CRUDRepository(Generic[M]):
    """Generic repository implementing reusable CRUD methods."""

    model: Type[M]

    def __init__(self, session: Session):
        self.session = session

    def create(self, **values) -> M:
        obj = self.model(**values)
        self.session.add(obj)
        self.session.flush()
        return obj

    def get(self, obj_id: int) -> Optional[M]:
        return self.session.get(self.model, int(obj_id))

    def first(self, **filters) -> Optional[M]:
        statement = select(self.model)
        for key, value in filters.items():
            statement = statement.where(getattr(self.model, key) == value)
        return self.session.execute(statement).scalars().first()

    def all(self, **filters) -> list[M]:
        statement = select(self.model)
        for key, value in filters.items():
            statement = statement.where(getattr(self.model, key) == value)
        return list(self.session.execute(statement).scalars().all())

    def count(self, **filters) -> int:
        statement = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            statement = statement.where(getattr(self.model, key) == value)
        return int(self.session.execute(statement).scalar_one())

    def update(self, obj, **values) -> M:
        for key, value in values.items():
            setattr(obj, key, value)
        self.session.flush()
        return obj

    def update_by_id(self, obj_id: int, **values) -> bool:
        statement = (
            sa_update(self.model)
            .where(self.model.id == int(obj_id))
            .values(**values)
        )
        result = self.session.execute(statement)
        return result.rowcount > 0

    def delete(self, obj) -> None:
        self.session.delete(obj)
        self.session.flush()

    def delete_by_id(self, obj_id: int) -> bool:
        statement = sa_delete(self.model).where(self.model.id == int(obj_id))
        result = self.session.execute(statement)
        return result.rowcount > 0

    def flush(self) -> None:
        self.session.flush()


class TransactionRepository(CRUDRepository[Transaction]):
    model = Transaction

    def existing_fingerprints(self, records: list[dict]) -> set:
        """Return the set of (date, description, amount) fingerprints already stored."""
        dates = {record.get("date") for record in records if record.get("date")}
        if not dates:
            return set()
        rows = self.session.execute(
            select(Transaction.date, Transaction.description, Transaction.amount).where(
                Transaction.date.in_(dates)
            )
        ).all()
        return {(row[0], row[1], float(row[2])) for row in rows}

    def fingerprint_of(self, date: str, description: str, amount: float) -> tuple:
        return (date, description, float(amount))


class BudgetRepository(CRUDRepository[Budget]):
    model = Budget

    def get_monthly(self) -> Optional[Budget]:
        return self.first(scope="monthly")

    def get_category(self, category: str) -> Optional[Budget]:
        return self.first(scope="category", category=category)

    def get_all_sorted(self) -> list[Budget]:
        rows = self.all(scope="category")
        return sorted(rows, key=lambda b: (b.category or "").lower())


class BillRepository(CRUDRepository[Bill]):
    model = Bill


class InvestmentRepository(CRUDRepository[Investment]):
    model = Investment


class UserRepository(CRUDRepository[User]):
    model = User

    def by_username(self, username: str) -> Optional[User]:
        return self.first(username=username)

    def by_username_case_insensitive(self, username: str) -> Optional[User]:
        statement = select(User).where(User.username.ilike(username))
        return self.session.execute(statement).scalars().first()


class ReportRepository(CRUDRepository[Report]):
    model = Report

    def by_month(self, year: int, month: int, user_id: Optional[int] = None) -> Optional[Report]:
        return self.first(year=year, month=month, user_id=user_id)

    def list_ordered(self, limit: Optional[int] = None) -> list[Report]:
        statement = select(Report).order_by(Report.year.desc(), Report.month.desc())
        if limit:
            statement = statement.limit(int(limit))
        return list(self.session.execute(statement).scalars().all())


class HistoryRepository(CRUDRepository[History]):
    model = History


def log_history(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    user_id: Optional[int] = None,
) -> History:
    """Persist an audit-log entry. Details are JSON-serialised safely."""
    payload = None
    if details is not None:
        try:
            payload = json.dumps(details, default=str)
        except (TypeError, ValueError):
            payload = json.dumps({"data": str(details)})
    return HistoryRepository(session).create(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=payload,
        user_id=user_id,
    )
