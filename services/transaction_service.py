import datetime as dt
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from database.database import DB_PATH, get_connection, init_db
from services.ai_service import AIService
from utils.excel_reader import parse_date

DEFAULT_CATEGORY = "Others"


def categorize(description: str, amount: float | None) -> str:
    return AIService().categorize(description, amount)


class TransactionService:
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

    @staticmethod
    def _normalise_date(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, pd.Timestamp):
            if pd.isna(value):
                return None
            return value.date().isoformat()
        if isinstance(value, dt.datetime):
            return value.date().isoformat()
        if isinstance(value, dt.date):
            return value.isoformat()
        text = str(value).strip()
        if not text or text.lower() in ("nan", "nat", "none", "n/a"):
            return None
        parsed = parse_date(text)
        return parsed.isoformat() if parsed else None

    @staticmethod
    def _as_iso(value) -> str | None:
        if value is None:
            return None
        if isinstance(value, dt.datetime):
            return value.date().isoformat()
        if isinstance(value, dt.date):
            return value.isoformat()
        return str(value)

    def add_transaction(
        self,
        date,
        description: str,
        amount: float,
        category: str | None = None,
        balance: float | None = None,
        source: str | None = None,
    ) -> int | None:
        date_iso = self._normalise_date(date)
        description = str(description).strip()
        if not date_iso or not description or amount is None:
            return None
        amount = float(amount)
        category = category or categorize(description, amount)
        with self._connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO transactions (date, description, category, amount, balance, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (date_iso, description, category, amount, balance, source),
            )
            conn.commit()
            return cursor.lastrowid if cursor.rowcount else None

    def add_transactions(self, records: list[dict]) -> tuple[int, int]:
        inserted = 0
        skipped = 0
        with self._connection() as conn:
            for record in records:
                date_iso = self._normalise_date(record.get("date"))
                description = str(record.get("description", "")).strip()
                amount = record.get("amount")
                if not date_iso or not description or amount is None:
                    skipped += 1
                    continue
                try:
                    amount = float(amount)
                except (TypeError, ValueError):
                    skipped += 1
                    continue
                category = record.get("category") or categorize(description, amount)
                balance = record.get("balance")
                balance = float(balance) if balance is not None else None
                source = record.get("source")
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO transactions (date, description, category, amount, balance, source) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (date_iso, description, category, amount, balance, source),
                )
                if cursor.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            conn.commit()
        return inserted, skipped

    def import_dataframe(self, frame: pd.DataFrame) -> tuple[int, int, int]:
        if frame is None or frame.empty:
            return 0, 0, 0
        records = []
        for _, row in frame.iterrows():
            records.append(
                {
                    "date": row.get("date"),
                    "description": row.get("description"),
                    "amount": row.get("amount"),
                    "balance": row.get("balance"),
                    "source": row.get("source"),
                }
            )
        inserted, skipped = self.add_transactions(records)
        return len(records), inserted, skipped

    def get_all(self) -> pd.DataFrame:
        return self._query()

    def get_transactions(
        self,
        search: str | None = None,
        start=None,
        end=None,
        categories: list[str] | None = None,
    ) -> pd.DataFrame:
        return self._query(search=search, start=start, end=end, categories=categories)

    def search(self, query: str) -> pd.DataFrame:
        return self._query(search=query)

    def filter_by_date(self, start=None, end=None) -> pd.DataFrame:
        return self._query(start=start, end=end)

    def filter_by_category(self, categories: list[str]) -> pd.DataFrame:
        return self._query(categories=categories)

    def _query(
        self,
        search: str | None = None,
        start=None,
        end=None,
        categories: list[str] | None = None,
    ) -> pd.DataFrame:
        clauses = []
        params: list = []
        if search:
            clauses.append("(description LIKE ? OR category LIKE ?)")
            pattern = f"%{search}%"
            params.extend([pattern, pattern])
        start_iso = self._as_iso(start)
        end_iso = self._as_iso(end)
        if start_iso:
            clauses.append("date >= ?")
            params.append(start_iso)
        if end_iso:
            clauses.append("date <= ?")
            params.append(end_iso)
        if categories:
            placeholders = ", ".join("?" for _ in categories)
            clauses.append(f"category IN ({placeholders})")
            params.extend(categories)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            "SELECT id, date, description, category, amount, balance, source, created_at "
            f"FROM transactions {where} ORDER BY date DESC, id DESC"
        )
        with self._connection() as conn:
            frame = pd.read_sql_query(sql, conn, params=params)
        if frame.empty:
            return frame
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        return frame

    def get_by_id(self, transaction_id: int) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id, date, description, category, amount, balance, source FROM transactions WHERE id = ?",
                (int(transaction_id),),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_categories(self) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT category FROM transactions ORDER BY category"
            ).fetchall()
        return [row["category"] for row in rows]

    def update_category(self, transaction_id: int, category: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "UPDATE transactions SET category = ? WHERE id = ?",
                (str(category).strip(), int(transaction_id)),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete(self, transaction_id: int) -> bool:
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM transactions WHERE id = ?",
                (int(transaction_id),),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> dict:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count, "
                "COALESCE(SUM(CASE WHEN amount > 0 THEN amount END), 0) AS income, "
                "COALESCE(SUM(CASE WHEN amount < 0 THEN -amount END), 0) AS expense "
                "FROM transactions"
            ).fetchone()
        return {"count": row["count"], "income": row["income"], "expense": row["expense"]}

    def get_date_range(self) -> tuple[dt.date | None, dt.date | None]:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM transactions"
            ).fetchone()
        if row is None or row["min_date"] is None or row["max_date"] is None:
            return None, None
        return dt.date.fromisoformat(row["min_date"]), dt.date.fromisoformat(row["max_date"])
