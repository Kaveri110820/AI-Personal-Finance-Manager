import datetime as dt
from pathlib import Path

import pandas as pd
from sqlalchemy import func, or_, select

from database.crud import TransactionRepository, log_history
from database.database import DB_PATH, init_db, session_scope
from database.models import Transaction
from services.ai_service import AIService
from utils.excel_reader import parse_date

DEFAULT_CATEGORY = "Others"

_PUBLIC_COLUMNS = ("id", "date", "description", "category", "amount", "balance", "source")
_QUERY_COLUMNS = ("id", "date", "description", "category", "amount", "balance", "source", "created_at")


def categorize(description: str, amount: float | None) -> str:
    return AIService().categorize(description, amount)


class TransactionService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        init_db(self.db_path)

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
        with session_scope(self.db_path) as session:
            repo = TransactionRepository(session)
            fingerprint = repo.fingerprint_of(date_iso, description, amount)
            if fingerprint in repo.existing_fingerprints(
                [{"date": date_iso, "description": description, "amount": amount}]
            ):
                return None
            obj = repo.create(
                date=date_iso,
                description=description,
                category=category,
                amount=amount,
                balance=balance,
                source=source,
            )
            log_history(
                session,
                "transaction_added",
                "transaction",
                entity_id=obj.id,
                details={
                    "date": date_iso,
                    "description": description,
                    "category": category,
                    "amount": amount,
                },
            )
            return int(obj.id)

    def add_transactions(self, records: list[dict]) -> tuple[int, int]:
        valid: list[dict] = []
        skipped = 0
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
            valid.append(
                {
                    "date": date_iso,
                    "description": description,
                    "category": category,
                    "amount": amount,
                    "balance": balance,
                    "source": source,
                }
            )

        with session_scope(self.db_path) as session:
            repo = TransactionRepository(session)
            existing = repo.existing_fingerprints(valid)
            to_insert = [
                record
                for record in valid
                if repo.fingerprint_of(
                    record["date"], record["description"], record["amount"]
                )
                not in existing
            ]
            skipped += len(valid) - len(to_insert)
            if to_insert:
                session.add_all(
                    [
                        Transaction(
                            date=r["date"],
                            description=r["description"],
                            category=r["category"],
                            amount=r["amount"],
                            balance=r["balance"],
                            source=r["source"],
                        )
                        for r in to_insert
                    ]
                )
                session.flush()
                log_history(
                    session,
                    "transactions_imported",
                    "transaction",
                    details={"inserted": len(to_insert), "skipped": skipped},
                )
        return len(to_insert), skipped

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
        conditions = []
        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Transaction.description.like(pattern),
                    Transaction.category.like(pattern),
                )
            )
        start_iso = self._as_iso(start)
        end_iso = self._as_iso(end)
        if start_iso:
            conditions.append(Transaction.date >= start_iso)
        if end_iso:
            conditions.append(Transaction.date <= end_iso)
        if categories:
            conditions.append(Transaction.category.in_(categories))

        statement = (
            select(Transaction)
            .where(*conditions)
            .order_by(Transaction.date.desc(), Transaction.id.desc())
        )
        with session_scope(self.db_path) as session:
            rows = list(session.execute(statement).scalars().all())
        frame = pd.DataFrame([row.to_dict() for row in rows], columns=_QUERY_COLUMNS)
        if frame.empty:
            return frame
        frame["date"] = pd.to_datetime(frame["date"]).dt.date
        return frame

    def get_by_id(self, transaction_id: int) -> dict | None:
        with session_scope(self.db_path) as session:
            obj = TransactionRepository(session).get(int(transaction_id))
            if obj is None:
                return None
            return {column: getattr(obj, column) for column in _PUBLIC_COLUMNS}

    def get_categories(self) -> list[str]:
        with session_scope(self.db_path) as session:
            rows = session.execute(
                select(Transaction.category)
                .distinct()
                .order_by(Transaction.category)
            ).scalars().all()
        return [str(category) for category in rows]

    def update_category(self, transaction_id: int, category: str) -> bool:
        with session_scope(self.db_path) as session:
            repo = TransactionRepository(session)
            updated = repo.update_by_id(
                int(transaction_id), category=str(category).strip()
            )
            if updated:
                log_history(
                    session,
                    "category_changed",
                    "transaction",
                    entity_id=int(transaction_id),
                    details={"category": str(category).strip()},
                )
            return updated

    def delete(self, transaction_id: int) -> bool:
        with session_scope(self.db_path) as session:
            repo = TransactionRepository(session)
            obj = repo.get(int(transaction_id))
            if obj is None:
                return False
            log_history(
                session,
                "transaction_deleted",
                "transaction",
                entity_id=int(transaction_id),
                details={"description": obj.description, "amount": obj.amount},
            )
            repo.delete(obj)
            return True

    def get_stats(self) -> dict:
        with session_scope(self.db_path) as session:
            count = int(
                session.execute(
                    select(func.count()).select_from(Transaction)
                ).scalar_one()
            )
            income = float(
                session.execute(
                    select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                        Transaction.amount > 0
                    )
                ).scalar_one()
            )
            expense = float(
                session.execute(
                    select(
                        func.coalesce(func.sum(-Transaction.amount), 0)
                    ).where(Transaction.amount < 0)
                ).scalar_one()
            )
        return {"count": count, "income": income, "expense": expense}

    def get_date_range(self) -> tuple[dt.date | None, dt.date | None]:
        with session_scope(self.db_path) as session:
            min_date, max_date = session.execute(
                select(func.min(Transaction.date), func.max(Transaction.date))
            ).one()
        if min_date is None or max_date is None:
            return None, None
        return dt.date.fromisoformat(min_date), dt.date.fromisoformat(max_date)
