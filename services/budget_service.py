import calendar
import datetime as dt
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from database.crud import BudgetRepository, log_history
from database.database import DB_PATH, init_db, session_scope
from database.models import Budget, Transaction
from services.ai_service import CATEGORIES


def _pct(budget: float, spent: float) -> float:
    if budget is None or budget <= 0:
        return 0.0
    return float(min(round(spent / budget * 100, 1), 100.0))


class BudgetService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        init_db(self.db_path)

    def add_monthly_budget(self, amount: float) -> int:
        amount = float(amount)
        with session_scope(self.db_path) as session:
            repo = BudgetRepository(session)
            existing = repo.get_monthly()
            if existing:
                repo.update(existing, amount=amount)
                log_history(
                    session,
                    "budget_updated",
                    "budget",
                    entity_id=existing.id,
                    details={"scope": "monthly", "amount": amount},
                )
                return int(existing.id)
            obj = repo.create(scope="monthly", category=None, amount=amount)
            log_history(
                session,
                "budget_added",
                "budget",
                entity_id=obj.id,
                details={"scope": "monthly", "amount": amount},
            )
            return int(obj.id)

    def add_category_budget(self, category: str, amount: float) -> int:
        category = str(category).strip()
        amount = float(amount)
        with session_scope(self.db_path) as session:
            repo = BudgetRepository(session)
            existing = repo.get_category(category)
            if existing:
                repo.update(existing, amount=amount)
                log_history(
                    session,
                    "budget_updated",
                    "budget",
                    entity_id=existing.id,
                    details={"scope": "category", "category": category, "amount": amount},
                )
                return int(existing.id)
            obj = repo.create(scope="category", category=category, amount=amount)
            log_history(
                session,
                "budget_added",
                "budget",
                entity_id=obj.id,
                details={"scope": "category", "category": category, "amount": amount},
            )
            return int(obj.id)

    def update_budget(self, budget_id: int, amount: float) -> bool:
        with session_scope(self.db_path) as session:
            repo = BudgetRepository(session)
            updated = repo.update_by_id(int(budget_id), amount=float(amount))
            if updated:
                log_history(
                    session,
                    "budget_updated",
                    "budget",
                    entity_id=int(budget_id),
                    details={"amount": float(amount)},
                )
            return updated

    def delete_budget(self, budget_id: int) -> bool:
        with session_scope(self.db_path) as session:
            repo = BudgetRepository(session)
            obj = repo.get(int(budget_id))
            if obj is None:
                return False
            log_history(
                session,
                "budget_deleted",
                "budget",
                entity_id=int(budget_id),
                details={"scope": obj.scope, "category": obj.category},
            )
            repo.delete(obj)
            return True

    def get_budget(self, budget_id: int) -> dict | None:
        with session_scope(self.db_path) as session:
            obj = BudgetRepository(session).get(int(budget_id))
            return obj.to_dict() if obj else None

    def get_budgets(self) -> pd.DataFrame:
        with session_scope(self.db_path) as session:
            rows = session.execute(
                select(Budget).order_by(Budget.scope, Budget.category)
            ).scalars().all()
        return pd.DataFrame([row.to_dict() for row in rows])

    def get_monthly_budget(self) -> dict | None:
        with session_scope(self.db_path) as session:
            obj = BudgetRepository(session).get_monthly()
            return obj.to_dict() if obj else None

    def get_category_budgets(self) -> list[dict]:
        with session_scope(self.db_path) as session:
            rows = BudgetRepository(session).all(scope="category")
        return [row.to_dict() for row in rows]

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[str, str]:
        first = dt.date(year, month, 1)
        last = dt.date(year, month, calendar.monthrange(year, month)[1])
        return first.isoformat(), last.isoformat()

    def get_spending(self, year: int, month: int) -> pd.DataFrame:
        start, end = self._month_bounds(year, month)
        with session_scope(self.db_path) as session:
            rows = session.execute(
                select(Transaction.category, func.coalesce(func.sum(-Transaction.amount), 0).label("spent"))
                .where(
                    Transaction.amount < 0,
                    Transaction.date >= start,
                    Transaction.date <= end,
                )
                .group_by(Transaction.category)
            ).all()
        return pd.DataFrame(
            [{"category": row[0], "spent": float(row[1])} for row in rows],
            columns=["category", "spent"],
        )

    def get_total_spent(self, year: int, month: int) -> float:
        start, end = self._month_bounds(year, month)
        with session_scope(self.db_path) as session:
            total = session.execute(
                select(func.coalesce(func.sum(-Transaction.amount), 0)).where(
                    Transaction.amount < 0,
                    Transaction.date >= start,
                    Transaction.date <= end,
                )
            ).scalar_one()
        return float(total)

    def get_overview(self, year: int, month: int) -> pd.DataFrame:
        spending = self.get_spending(year, month)
        spent_by_category = dict(zip(spending["category"], spending["spent"]))
        total_spent = self.get_total_spent(year, month)

        rows = []
        monthly = self.get_monthly_budget()
        if monthly:
            spent = total_spent
            rows.append(
                {
                    "id": monthly["id"],
                    "scope": "monthly",
                    "name": "Monthly total",
                    "category": None,
                    "amount": monthly["amount"],
                    "spent": spent,
                    "remaining": monthly["amount"] - spent,
                    "percent": _pct(monthly["amount"], spent),
                    "overspent": spent > monthly["amount"],
                }
            )

        for budget in self.get_category_budgets():
            spent = spent_by_category.get(budget["category"], 0.0)
            rows.append(
                {
                    "id": budget["id"],
                    "scope": "category",
                    "name": budget["category"],
                    "category": budget["category"],
                    "amount": budget["amount"],
                    "spent": spent,
                    "remaining": budget["amount"] - spent,
                    "percent": _pct(budget["amount"], spent),
                    "overspent": spent > budget["amount"],
                }
            )

        if rows:
            category_rows = [row for row in rows if row["category"] is not None]
            category_rows.sort(
                key=lambda row: CATEGORIES.index(row["category"])
                if row["category"] in CATEGORIES
                else len(CATEGORIES)
            )
            rows = [row for row in rows if row["category"] is None] + category_rows

        return pd.DataFrame(rows)
