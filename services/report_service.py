import calendar
import datetime as dt
from pathlib import Path

import pandas as pd

from database.database import DB_PATH
from services.bill_service import BillService
from services.budget_service import BudgetService
from services.investment_service import InvestmentService
from services.transaction_service import TransactionService


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

        return {
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
