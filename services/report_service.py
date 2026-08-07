import calendar
import datetime as dt
import json
from pathlib import Path

import pandas as pd

from database.crud import ReportRepository
from database.database import DB_PATH, session_scope
from services.bill_service import BillService
from services.budget_service import BudgetService
from services.investment_service import InvestmentService
from services.transaction_service import TransactionService


def _frame_to_json(frame: pd.DataFrame | None) -> str | None:
    if frame is None or getattr(frame, "empty", True):
        return None
    return frame.to_json(orient="records", date_format="iso")


class ReportService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.tx = TransactionService(self.db_path)
        self.budgets = BudgetService(self.db_path)
        self.bills = BillService(self.db_path)
        self.investments = InvestmentService(self.db_path)

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
        first = dt.date(year, month, 1)
        last = dt.date(year, month, calendar.monthrange(year, month)[1])
        return first, last

    def generate(self, year: int, month: int) -> dict:
        start, end = self._month_bounds(year, month)

        transactions = self.tx.get_transactions(start=start, end=end)
        income = float(transactions.loc[transactions["amount"] > 0, "amount"].sum())
        expenses = transactions.loc[transactions["amount"] < 0]
        expense = float(-expenses["amount"].sum())
        savings = round(income - expense, 2)
        savings_rate = round(savings / income * 100, 1) if income > 0 else 0.0

        categories = (
            expenses.groupby("category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .reset_index()
        )
        categories.columns = ["category", "amount"]

        budget_overview = self.budgets.get_overview(year, month)
        monthly_budget = self.budgets.get_monthly_budget()

        all_bills = self.bills.get_bills()
        if all_bills.empty:
            bills = all_bills
        else:
            bills = all_bills[
                (all_bills["due_date"] >= start.isoformat())
                & (all_bills["due_date"] <= end.isoformat())
            ].copy()
        bills_total = float(bills["amount"].sum()) if not bills.empty else 0.0
        bills_paid = (
            float(bills.loc[bills["status"] == "paid", "amount"].sum())
            if not bills.empty
            else 0.0
        )

        investments = self.investments.get_investments()
        investment_total = (
            float(investments["amount"].sum()) if not investments.empty else 0.0
        )
        allocation = (
            investments.groupby("investment_type")["amount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
        )
        allocation.columns = ["investment_type", "amount"]
        if not allocation.empty:
            allocation["percent"] = (
                allocation["amount"] / allocation["amount"].sum() * 100
            ).round(1)

        report = {
            "start": start,
            "end": end,
            "income": income,
            "expense": expense,
            "savings": savings,
            "savings_rate": savings_rate,
            "categories": categories,
            "budget_overview": budget_overview,
            "monthly_budget": monthly_budget,
            "bills": bills,
            "bills_total": bills_total,
            "bills_paid": bills_paid,
            "bills_pending": round(bills_total - bills_paid, 2),
            "investments": investments,
            "investment_total": investment_total,
            "allocation": allocation,
        }

        self._save_snapshot(year, month, report)
        return report

    def _save_snapshot(self, year: int, month: int, report: dict) -> None:
        monthly_budget = report.get("monthly_budget")
        values = {
            "year": int(year),
            "month": int(month),
            "income": round(float(report.get("income", 0)), 2),
            "expense": round(float(report.get("expense", 0)), 2),
            "savings": round(float(report.get("savings", 0)), 2),
            "savings_rate": float(report.get("savings_rate", 0)),
            "budget_total": float(monthly_budget["amount"]) if monthly_budget else None,
            "bills_total": round(float(report.get("bills_total", 0)), 2),
            "bills_paid": round(float(report.get("bills_paid", 0)), 2),
            "bills_pending": round(float(report.get("bills_pending", 0)), 2),
            "investment_total": round(float(report.get("investment_total", 0)), 2),
            "categories_json": _frame_to_json(report.get("categories")),
            "budget_overview_json": _frame_to_json(report.get("budget_overview")),
            "bills_json": _frame_to_json(report.get("bills")),
            "allocation_json": _frame_to_json(report.get("allocation")),
        }
        with session_scope(self.db_path) as session:
            repo = ReportRepository(session)
            existing = repo.by_month(year, month)
            if existing:
                repo.update(existing, **values)
            else:
                repo.create(**values)

    def update_summary(self, year: int, month: int, summary: dict) -> bool:
        try:
            payload = json.dumps(summary, default=str)
        except (TypeError, ValueError):
            payload = json.dumps({"data": str(summary)})
        with session_scope(self.db_path) as session:
            repo = ReportRepository(session)
            report = repo.by_month(int(year), int(month))
            if report is None:
                return False
            repo.update(report, summary_json=payload)
            return True

    def get_report(self, year: int, month: int) -> dict | None:
        with session_scope(self.db_path) as session:
            report = ReportRepository(session).by_month(int(year), int(month))
            return report.to_dict() if report else None

    def list_reports(self, limit: int | None = None) -> list[dict]:
        with session_scope(self.db_path) as session:
            rows = ReportRepository(session).list_ordered(limit)
        return [row.to_dict() for row in rows]
