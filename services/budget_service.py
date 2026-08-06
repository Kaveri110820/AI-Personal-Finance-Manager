import calendar
import datetime as dt
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from database.database import DB_PATH, get_connection, init_db
from services.ai_service import CATEGORIES


def _pct(budget: float, spent: float) -> float:
    if budget is None or budget <= 0:
        return 0.0
    return float(min(round(spent / budget * 100, 1), 100.0))


class BudgetService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        init_db(self.db_path)

    @contextmanager
    def _connection(self):
        conn = get_connection(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def add_monthly_budget(self, amount: float) -> int:
        amount = float(amount)
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM budgets WHERE scope = 'monthly'"
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE budgets SET amount = ? WHERE id = ?",
                    (amount, row["id"]),
                )
                conn.commit()
                return int(row["id"])
            cursor = conn.execute(
                "INSERT INTO budgets (scope, category, amount) VALUES ('monthly', NULL, ?)",
                (amount,),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def add_category_budget(self, category: str, amount: float) -> int:
        category = str(category).strip()
        amount = float(amount)
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id FROM budgets WHERE scope = 'category' AND category = ?",
                (category,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE budgets SET amount = ? WHERE id = ?",
                    (amount, row["id"]),
                )
                conn.commit()
                return int(row["id"])
            cursor = conn.execute(
                "INSERT INTO budgets (scope, category, amount) VALUES ('category', ?, ?)",
                (category, amount),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_budget(self, budget_id: int, amount: float) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE budgets SET amount = ? WHERE id = ?",
                (float(amount), int(budget_id)),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_budget(self, budget_id: int) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM budgets WHERE id = ?",
                (int(budget_id),),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_budget(self, budget_id: int) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, scope, category, amount FROM budgets WHERE id = ?",
                (int(budget_id),),
            ).fetchone()
        return dict(row) if row else None

    def get_budgets(self) -> pd.DataFrame:
        with self._connection() as conn:
            frame = pd.read_sql_query(
                "SELECT id, scope, category, amount FROM budgets ORDER BY scope, category",
                conn,
            )
        return frame

    def get_monthly_budget(self) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, scope, category, amount FROM budgets WHERE scope = 'monthly'"
            ).fetchone()
        return dict(row) if row else None

    def get_category_budgets(self) -> list[dict]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT id, scope, category, amount FROM budgets WHERE scope = 'category'"
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[str, str]:
        first = dt.date(year, month, 1)
        last = dt.date(year, month, calendar.monthrange(year, month)[1])
        return first.isoformat(), last.isoformat()

    def get_spending(self, year: int, month: int) -> pd.DataFrame:
        start, end = self._month_bounds(year, month)
        with self._connection() as conn:
            frame = pd.read_sql_query(
                "SELECT category, COALESCE(SUM(-amount), 0) AS spent "
                "FROM transactions "
                "WHERE amount < 0 AND date >= ? AND date <= ? "
                "GROUP BY category",
                conn,
                params=(start, end),
            )
        return frame

    def get_total_spent(self, year: int, month: int) -> float:
        start, end = self._month_bounds(year, month)
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(-amount), 0) AS spent "
                "FROM transactions WHERE amount < 0 AND date >= ? AND date <= ?",
                (start, end),
            ).fetchone()
        return float(row["spent"])

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
