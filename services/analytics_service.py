import calendar
import datetime as dt
from pathlib import Path

import pandas as pd

from database.database import DB_PATH
from services.bill_service import BillService
from services.budget_service import BudgetService
from services.investment_service import InvestmentService
from services.transaction_service import TransactionService


class AnalyticsService:
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

    def get_monthly_series(self, months: int = 12) -> pd.DataFrame:
        end = pd.Timestamp.today().normalize().to_period("M")
        periods = pd.period_range(end - (int(months) - 1), end, freq="M")
        frame = pd.DataFrame(
            {
                "month": periods,
                "label": [p.strftime("%b %Y") for p in periods],
            }
        ).set_index("month")

        transactions = self.tx.get_all()
        if not transactions.empty:
            transactions["month"] = pd.to_datetime(
                transactions["date"]
            ).dt.to_period("M")
            income = transactions.loc[transactions["amount"] > 0].groupby(
                "month"
            )["amount"].sum()
            expense = (
                transactions.loc[transactions["amount"] < 0]
                .groupby("month")["amount"]
                .sum()
                .abs()
            )
            frame["income"] = income.reindex(periods).fillna(0.0)
            frame["expense"] = expense.reindex(periods).fillna(0.0)
        else:
            frame["income"] = 0.0
            frame["expense"] = 0.0

        frame = frame.reset_index()
        frame["savings"] = frame["income"] - frame["expense"]
        frame["cumulative_savings"] = frame["savings"].cumsum()
        return frame

    def get_category_distribution(self, year: int, month: int) -> pd.DataFrame:
        start, end = self._month_bounds(year, month)
        transactions = self.tx.get_transactions(start=start, end=end)
        if transactions.empty:
            return pd.DataFrame(columns=["category", "amount"])
        expenses = transactions.loc[transactions["amount"] < 0]
        if expenses.empty:
            return pd.DataFrame(columns=["category", "amount"])
        frame = (
            expenses.groupby("category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
            .reset_index()
        )
        frame.columns = ["category", "amount"]
        return frame

    def get_budget_utilization(self, year: int, month: int) -> pd.DataFrame:
        overview = self.budgets.get_overview(year, month)
        if overview.empty:
            return pd.DataFrame(
                columns=["name", "amount", "spent", "percent", "overspent"]
            )
        return overview[["name", "amount", "spent", "percent", "overspent"]].copy()

    def get_investment_allocation(self) -> pd.DataFrame:
        return self.investments.get_allocation()

    def get_top_expenses(
        self, year: int, month: int, n: int = 10
    ) -> pd.DataFrame:
        start, end = self._month_bounds(year, month)
        transactions = self.tx.get_transactions(start=start, end=end)
        if transactions.empty:
            return pd.DataFrame(
                columns=["date", "description", "category", "amount"]
            )
        expenses = transactions.loc[transactions["amount"] < 0].copy()
        if expenses.empty:
            return pd.DataFrame(
                columns=["date", "description", "category", "amount"]
            )
        frame = expenses.nsmallest(int(n), "amount")[
            ["date", "description", "category", "amount"]
        ].reset_index(drop=True)
        return frame

    def get_month_summary(self, year: int, month: int) -> dict:
        start, end = self._month_bounds(year, month)
        transactions = self.tx.get_transactions(start=start, end=end)
        income = float(transactions.loc[transactions["amount"] > 0, "amount"].sum())
        expense = float(
            -transactions.loc[transactions["amount"] < 0, "amount"].sum()
        )
        savings = round(income - expense, 2)
        rate = round(savings / income * 100, 1) if income > 0 else 0.0
        return {
            "income": income,
            "expense": expense,
            "savings": savings,
            "savings_rate": rate,
        }
