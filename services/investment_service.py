from pathlib import Path

import pandas as pd
from sqlalchemy import func, select

from database.crud import InvestmentRepository, log_history
from database.database import DB_PATH, init_db, session_scope
from database.models import Investment

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

    @staticmethod
    def _frame(rows: list[Investment]) -> pd.DataFrame:
        return pd.DataFrame(
            [row.to_dict() for row in rows],
            columns=["id", "name", "investment_type", "amount"],
        )

    def add_investment(self, name: str, investment_type: str, amount: float) -> int:
        name = str(name).strip()
        if investment_type not in INVESTMENT_TYPES:
            raise ValueError(f"Unknown investment type: {investment_type}")
        with session_scope(self.db_path) as session:
            obj = InvestmentRepository(session).create(
                name=name,
                investment_type=investment_type,
                amount=float(amount),
            )
            log_history(
                session,
                "investment_added",
                "investment",
                entity_id=obj.id,
                details={"name": name, "investment_type": investment_type, "amount": float(amount)},
            )
            return int(obj.id)

    def update_investment(
        self, investment_id: int, name: str, investment_type: str, amount: float
    ) -> bool:
        name = str(name).strip()
        if investment_type not in INVESTMENT_TYPES:
            raise ValueError(f"Unknown investment type: {investment_type}")
        with session_scope(self.db_path) as session:
            repo = InvestmentRepository(session)
            updated = repo.update_by_id(
                int(investment_id),
                name=name,
                investment_type=investment_type,
                amount=float(amount),
            )
            if updated:
                log_history(
                    session,
                    "investment_updated",
                    "investment",
                    entity_id=int(investment_id),
                    details={"name": name, "investment_type": investment_type, "amount": float(amount)},
                )
            return updated

    def delete_investment(self, investment_id: int) -> bool:
        with session_scope(self.db_path) as session:
            repo = InvestmentRepository(session)
            obj = repo.get(int(investment_id))
            if obj is None:
                return False
            log_history(
                session,
                "investment_deleted",
                "investment",
                entity_id=int(investment_id),
                details={"name": obj.name},
            )
            repo.delete(obj)
            return True

    def get_investment(self, investment_id: int) -> dict | None:
        with session_scope(self.db_path) as session:
            obj = InvestmentRepository(session).get(int(investment_id))
            return obj.to_dict() if obj else None

    def get_investments(self) -> pd.DataFrame:
        with session_scope(self.db_path) as session:
            rows = session.execute(
                select(Investment).order_by(
                    Investment.investment_type, Investment.name
                )
            ).scalars().all()
        return self._frame(rows)

    def get_total(self) -> float:
        with session_scope(self.db_path) as session:
            total = session.execute(
                select(func.coalesce(func.sum(Investment.amount), 0))
            ).scalar_one()
        return float(total)

    def get_allocation(self) -> pd.DataFrame:
        with session_scope(self.db_path) as session:
            rows = session.execute(
                select(
                    Investment.investment_type,
                    func.coalesce(func.sum(Investment.amount), 0).label("amount"),
                    func.count().label("count"),
                )
                .group_by(Investment.investment_type)
                .order_by(func.sum(Investment.amount).desc())
            ).all()
        frame = pd.DataFrame(
            [
                {"investment_type": row[0], "amount": float(row[1]), "count": int(row[2])}
                for row in rows
            ],
            columns=["investment_type", "amount", "count"],
        )
        if not frame.empty:
            total = float(frame["amount"].sum())
            frame["percent"] = (
                (frame["amount"] / total * 100).round(1) if total else 0.0
            )
        return frame

    def get_stats(self) -> dict:
        with session_scope(self.db_path) as session:
            count = int(
                session.execute(select(func.count()).select_from(Investment)).scalar_one()
            )
        return {"count": count}
