from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from database.database import DB_PATH, get_connection, init_db

INVESTMENT_TYPES = [
    "Stocks",
    "Mutual Funds",
    "Gold",
    "Fixed Deposit",
    "Crypto",
]


class InvestmentService:
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

    def add_investment(self, name: str, investment_type: str, amount: float) -> int:
        name = str(name).strip()
        if investment_type not in INVESTMENT_TYPES:
            raise ValueError(f"Unknown investment type: {investment_type}")
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT INTO investments (name, investment_type, amount) "
                "VALUES (?, ?, ?)",
                (name, investment_type, float(amount)),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def update_investment(
        self, investment_id: int, name: str, investment_type: str, amount: float
    ) -> bool:
        name = str(name).strip()
        if investment_type not in INVESTMENT_TYPES:
            raise ValueError(f"Unknown investment type: {investment_type}")
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE investments SET name = ?, investment_type = ?, amount = ? "
                "WHERE id = ?",
                (name, investment_type, float(amount), int(investment_id)),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_investment(self, investment_id: int) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM investments WHERE id = ?",
                (int(investment_id),),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_investment(self, investment_id: int) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, name, investment_type, amount FROM investments WHERE id = ?",
                (int(investment_id),),
            ).fetchone()
        return dict(row) if row else None

    def get_investments(self) -> pd.DataFrame:
        with self._connection() as conn:
            frame = pd.read_sql_query(
                "SELECT id, name, investment_type, amount FROM investments "
                "ORDER BY investment_type, name",
                conn,
            )
        return frame

    def get_total(self) -> float:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM investments"
            ).fetchone()
        return float(row["total"])

    def get_allocation(self) -> pd.DataFrame:
        with self._connection() as conn:
            frame = pd.read_sql_query(
                "SELECT investment_type, COALESCE(SUM(amount), 0) AS amount, "
                "COUNT(*) AS count "
                "FROM investments GROUP BY investment_type ORDER BY amount DESC",
                conn,
            )
        if not frame.empty:
            total = float(frame["amount"].sum())
            frame["percent"] = (
                (frame["amount"] / total * 100).round(1) if total else 0.0
            )
        return frame

    def get_stats(self) -> dict:
        with self._connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS n FROM investments"
            ).fetchone()["n"]
        return {"count": int(count)}
