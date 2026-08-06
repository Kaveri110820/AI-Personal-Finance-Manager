import calendar
import datetime as dt
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from database.database import DB_PATH, get_connection, init_db

VALID_STATUSES = ("pending", "paid")


class BillService:
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

    def add_bill(
        self, name: str, due_date: str, amount: float, status: str = "pending"
    ) -> int:
        name = str(name).strip()
        if status not in VALID_STATUSES:
            status = "pending"
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO bills (name, due_date, amount, status) VALUES (?, ?, ?, ?)",
                (name, str(due_date), float(amount), status),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_bill(
        self,
        bill_id: int,
        name: str,
        due_date: str,
        amount: float,
        status: str,
    ) -> bool:
        if status not in VALID_STATUSES:
            status = "pending"
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE bills SET name = ?, due_date = ?, amount = ?, status = ? "
                "WHERE id = ?",
                (
                    str(name).strip(),
                    str(due_date),
                    float(amount),
                    status,
                    int(bill_id),
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def set_status(self, bill_id: int, status: str) -> bool:
        if status not in VALID_STATUSES:
            return False
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE bills SET status = ? WHERE id = ?",
                (status, int(bill_id)),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_bill(self, bill_id: int) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM bills WHERE id = ?",
                (int(bill_id),),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_bill(self, bill_id: int) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, name, due_date, amount, status FROM bills WHERE id = ?",
                (int(bill_id),),
            ).fetchone()
        return dict(row) if row else None

    def get_bills(self) -> pd.DataFrame:
        with self._connection() as conn:
            frame = pd.read_sql_query(
                "SELECT id, name, due_date, amount, status FROM bills "
                "ORDER BY due_date, name",
                conn,
            )
        return frame

    def _bills_where(self, where: str, params: tuple = ()) -> pd.DataFrame:
        with self._connection() as conn:
            frame = pd.read_sql_query(
                f"SELECT id, name, due_date, amount, status FROM bills "
                f"WHERE {where} ORDER BY due_date, name",
                conn,
                params=params,
            )
        return frame

    def get_due_today(self) -> pd.DataFrame:
        today = dt.date.today().isoformat()
        return self._bills_where(
            "status = 'pending' AND due_date = ?", (today,)
        )

    def get_overdue(self) -> pd.DataFrame:
        today = dt.date.today().isoformat()
        return self._bills_where(
            "status = 'pending' AND due_date < ?", (today,)
        )

    def get_upcoming(self, days: int = 30) -> pd.DataFrame:
        today = dt.date.today().isoformat()
        horizon = (dt.date.today() + dt.timedelta(days=int(days))).isoformat()
        return self._bills_where(
            "status = 'pending' AND due_date >= ? AND due_date <= ?",
            (today, horizon),
        )

    def get_reminders(self, days: int = 30) -> pd.DataFrame:
        horizon = (dt.date.today() + dt.timedelta(days=int(days))).isoformat()
        return self._bills_where(
            "status = 'pending' AND due_date <= ?",
            (horizon,),
        )

    def get_monthly_total(self, year: int, month: int) -> float:
        start = dt.date(year, month, 1).isoformat()
        last = dt.date(year, month, calendar.monthrange(year, month)[1])
        end = last.isoformat()
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM bills "
                "WHERE status = 'pending' AND due_date >= ? AND due_date <= ?",
                (start, end),
            ).fetchone()
        return float(row["total"])

    def get_stats(self) -> dict:
        with self._connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM bills"
            ).fetchone()["n"]
            paid = conn.execute(
                "SELECT COUNT(*) AS n FROM bills WHERE status = 'paid'"
            ).fetchone()["n"]
            pending_total = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM bills "
                "WHERE status = 'pending'"
            ).fetchone()["total"]
        return {
            "total": int(total),
            "paid": int(paid),
            "pending": int(total) - int(paid),
            "pending_total": float(pending_total),
        }
