import calendar
import datetime as dt
from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from database.crud import BillRepository, log_history
from database.database import DB_PATH, init_db, session_scope
from database.models import Bill

VALID_STATUSES = ("pending", "paid")


class BillService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        init_db(self.db_path)

    @staticmethod
    def _frame(rows: list[Bill]) -> pd.DataFrame:
        return pd.DataFrame(
            [row.to_dict() for row in rows],
            columns=["id", "name", "due_date", "amount", "status"],
        )

    def add_bill(
        self, name: str, due_date: str, amount: float, status: str = "pending"
    ) -> int:
        name = str(name).strip()
        if status not in VALID_STATUSES:
            status = "pending"
        with session_scope(self.db_path) as session:
            obj = BillRepository(session).create(
                name=name,
                due_date=str(due_date),
                amount=float(amount),
                status=status,
            )
            log_history(
                session,
                "bill_added",
                "bill",
                entity_id=obj.id,
                details={"name": name, "due_date": str(due_date), "amount": float(amount), "status": status},
            )
            return int(obj.id)

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
        with session_scope(self.db_path) as session:
            repo = BillRepository(session)
            updated = repo.update_by_id(
                int(bill_id),
                name=str(name).strip(),
                due_date=str(due_date),
                amount=float(amount),
                status=status,
            )
            if updated:
                log_history(
                    session,
                    "bill_updated",
                    "bill",
                    entity_id=int(bill_id),
                    details={"name": str(name).strip(), "due_date": str(due_date), "amount": float(amount), "status": status},
                )
            return updated

    def set_status(self, bill_id: int, status: str) -> bool:
        if status not in VALID_STATUSES:
            return False
        with session_scope(self.db_path) as session:
            repo = BillRepository(session)
            updated = repo.update_by_id(int(bill_id), status=status)
            if updated:
                log_history(
                    session,
                    "bill_status_changed",
                    "bill",
                    entity_id=int(bill_id),
                    details={"status": status},
                )
            return updated

    def delete_bill(self, bill_id: int) -> bool:
        with session_scope(self.db_path) as session:
            repo = BillRepository(session)
            obj = repo.get(int(bill_id))
            if obj is None:
                return False
            log_history(
                session,
                "bill_deleted",
                "bill",
                entity_id=int(bill_id),
                details={"name": obj.name},
            )
            repo.delete(obj)
            return True

    def get_bill(self, bill_id: int) -> dict | None:
        with session_scope(self.db_path) as session:
            obj = BillRepository(session).get(int(bill_id))
            return obj.to_dict() if obj else None

    def _query(self, *conditions) -> pd.DataFrame:
        statement = (
            select(Bill)
            .where(*conditions)
            .order_by(Bill.due_date, Bill.name)
        )
        with session_scope(self.db_path) as session:
            rows = list(session.execute(statement).scalars().all())
        return self._frame(rows)

    def get_bills(self) -> pd.DataFrame:
        return self._query()

    def get_due_today(self) -> pd.DataFrame:
        today = dt.date.today().isoformat()
        return self._query(Bill.status == "pending", Bill.due_date == today)

    def get_overdue(self) -> pd.DataFrame:
        today = dt.date.today().isoformat()
        return self._query(Bill.status == "pending", Bill.due_date < today)

    def get_upcoming(self, days: int = 30) -> pd.DataFrame:
        today = dt.date.today().isoformat()
        horizon = (dt.date.today() + dt.timedelta(days=int(days))).isoformat()
        return self._query(
            Bill.status == "pending",
            Bill.due_date >= today,
            Bill.due_date <= horizon,
        )

    def get_reminders(self, days: int = 30) -> pd.DataFrame:
        horizon = (dt.date.today() + dt.timedelta(days=int(days))).isoformat()
        return self._query(Bill.status == "pending", Bill.due_date <= horizon)

    def get_monthly_total(self, year: int, month: int) -> float:
        start = dt.date(year, month, 1).isoformat()
        last = dt.date(year, month, calendar.monthrange(year, month)[1])
        end = last.isoformat()
        with session_scope(self.db_path) as session:
            total = session.execute(
                select(func.coalesce(func.sum(Bill.amount), 0)).where(
                    Bill.status == "pending",
                    Bill.due_date >= start,
                    Bill.due_date <= end,
                )
            ).scalar_one()
        return float(total)

    def get_stats(self) -> dict:
        with session_scope(self.db_path) as session:
            total = int(
                session.execute(select(func.count()).select_from(Bill)).scalar_one()
            )
            paid = int(
                session.execute(
                    select(func.count()).select_from(Bill).where(Bill.status == "paid")
                ).scalar_one()
            )
            pending_total = float(
                session.execute(
                    select(func.coalesce(func.sum(Bill.amount), 0)).where(
                        Bill.status == "pending"
                    )
                ).scalar_one()
            )
        return {
            "total": total,
            "paid": paid,
            "pending": total - paid,
            "pending_total": pending_total,
        }
