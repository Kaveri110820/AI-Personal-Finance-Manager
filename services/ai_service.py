import json
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CATEGORIES = [
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "Healthcare",
    "Entertainment",
    "Education",
    "Salary",
    "Investment",
    "Others",
]

DEFAULT_MODEL = "gemini-3.5-flash"

_KEYWORD_RULES = [
    (
        "Education",
        [
            "tuition",
            "school",
            "university",
            "college",
            "course",
            "education",
            "training",
            "workshop",
            "seminar",
            "elearning",
            "udemy",
            "coursera",
            "textbook",
            "library",
            "student",
            "exam",
            "books",
        ],
    ),
    (
        "Healthcare",
        [
            "pharmacy",
            "chemist",
            "doctor",
            "hospital",
            "dentist",
            "medical",
            "clinic",
            "optical",
            "therapy",
            "prescription",
            "medicine",
            "gym",
            "fitness",
            "physio",
            "dental",
            "counselling",
        ],
    ),
    (
        "Entertainment",
        [
            "netflix",
            "spotify",
            "streaming",
            "subscription",
            "cinema",
            "movie",
            "music",
            "game",
            "entertainment",
            "amazon prime",
            "hulu",
            "disney",
            "youtube",
            "concert",
            "museum",
            "hobby",
            "theatre",
            "theater",
            "playstation",
            "xbox",
            "steam",
            "audible",
        ],
    ),
    (
        "Food",
        [
            "grocery",
            "supermarket",
            "groceries",
            "food",
            "restaurant",
            "cafe",
            "coffee",
            "starbucks",
            "mcdonald",
            "subway",
            "pizza",
            "dining",
            "delivery",
            "doordash",
            "ubereats",
            "uber eats",
            "grubhub",
            "bar",
            "pub",
            "takeaway",
            "tesco",
            "walmart",
            "aldi",
            "lidl",
            "costco",
            "kroger",
            "whole foods",
            "trader joe",
            "bakery",
            "breakfast",
            "lunch",
            "dinner",
            "snack",
            "dominos",
            "kfc",
            "burger",
        ],
    ),
    (
        "Travel",
        [
            "uber",
            "lyft",
            "taxi",
            "train",
            "bus",
            "metro",
            "flight",
            "airline",
            "hotel",
            "airbnb",
            "booking",
            "expedia",
            "car rental",
            "hertz",
            "avis",
            "petrol",
            "fuel",
            "gas station",
            "toll",
            "parking",
            "transit",
            "shell",
            "esso",
            "chevron",
            "travel",
            "trip",
            "vacation",
        ],
    ),
    (
        "Shopping",
        [
            "amazon",
            "target",
            "store",
            "mall",
            "shop",
            "shopping",
            "clothing",
            "apparel",
            "home depot",
            "ikea",
            "best buy",
            "e-commerce",
            "retail",
            "zara",
            "nike",
            "footwear",
            "electronics",
            "marketplace",
            "ebay",
            "etsy",
        ],
    ),
    (
        "Investment",
        [
            "investment",
            "invest",
            "stock",
            "shares",
            "dividend",
            "mutual fund",
            "etf",
            "trading",
            "brokerage",
            "robinhood",
            "interest",
            "portfolio",
            "crypto",
            "bitcoin",
            "bond",
            "fund",
        ],
    ),
    (
        "Salary",
        [
            "salary",
            "payroll",
            "wages",
            "paycheck",
            "income",
            "bonus",
            "commission",
            "freelance",
            "deposit",
            "transfer in",
            "stipend",
            "allowance",
            "refund",
            "rebate",
            "cashback",
            "invoice",
            "gift",
        ],
    ),
    (
        "Bills",
        [
            "rent",
            "mortgage",
            "electric",
            "electricity",
            "water",
            "internet",
            "broadband",
            "phone",
            "utility",
            "utilities",
            "energy",
            "gas bill",
            "mobile",
            "wifi",
            "cable",
            "insurance",
            "tv licence",
            "council",
            "tax",
            "bill",
            "payment",
            "emi",
            "loan",
            "credit card",
        ],
    ),
]

DISCRETIONARY_CATEGORIES = {"Food", "Shopping", "Entertainment", "Travel"}

SAVINGS_FACTORS = {
    "Food": 0.15,
    "Shopping": 0.15,
    "Entertainment": 0.15,
    "Travel": 0.10,
    "Bills": 0.05,
    "Healthcare": 0.05,
    "Education": 0.10,
}

SAVINGS_TIPS = {
    "Food": (
        "Cook at home more",
        "Takeaway, delivery and restaurants cost far more than home cooking. "
        "Trimming dining out by 15% is a realistic, painless saving.",
    ),
    "Shopping": (
        "Delay impulse purchases",
        "Shopping is the easiest category to cut. Waiting 72 hours before a "
        "non-essential buy typically removes about 15% of the spend.",
    ),
    "Entertainment": (
        "Trim subscriptions",
        "Streaming and entertainment subscriptions accumulate quietly. Dropping the "
        "services you rarely open can free up around 15% of this spend.",
    ),
    "Travel": (
        "Plan trips ahead",
        "Filling up and booking travel earlier cuts costs. Carpooling or using "
        "public transport a few days a week saves around 10%.",
    ),
    "Bills": (
        "Shop around for bills",
        "Utility and insurance providers differ wildly in price. Comparing plans "
        "and using less energy can shave about 5% off your bills.",
    ),
    "Healthcare": (
        "Review recurring health costs",
        "Generic medicines, pharmacy price checks and gym plan reviews can reduce "
        "healthcare spending by around 5%.",
    ),
    "Education": (
        "Use free learning resources",
        "Free courses, libraries and employer benefits can replace paid training. "
        "A 10% trim here is achievable.",
    ),
}

_CATEGORY_PROMPT = (
    "You are a personal finance assistant. Classify each transaction into exactly one "
    "of these categories: " + ", ".join(CATEGORIES) + ". "
    "Respond with JSON only and no commentary."
)


def _parse_json(text):
    if not text:
        return None
    text = str(text).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]|\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


class AIService:
    """Reusable AI client for Google AI Studio (Gemini).

    Provides four modules — expense categorization, savings suggestions, financial
    insights and monthly report summaries. Every module degrades gracefully to a
    built-in rule-based engine when no API key is configured or the API call fails.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = (
            api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        ).strip()
        self.model = (model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
        self.available = bool(self.api_key)
        self.provider = "gemini" if self.available else "fallback"
        self.last_error: str | None = None
        self.request_count = 0
        self._client = None

    # ------------------------------------------------------------------ plumbing

    def _get_client(self):
        if not self.available:
            return None
        if self._client is not None:
            return self._client
        try:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        except Exception as exc:  # noqa: BLE001 - library missing or bad config
            self.last_error = str(exc)
            self.available = False
            self.provider = "fallback"
            self._client = None
        return self._client

    def generate(self, prompt: str, *, response_json: bool = False):
        """Run a single Gemini call. Returns text (or parsed JSON) or None on failure."""
        client = self._get_client()
        if client is None:
            return None
        try:
            config = {"response_mime_type": "application/json"} if response_json else None
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            self.request_count += 1
            text = getattr(response, "text", None)
            if not text:
                self.last_error = "Empty response from model"
                return None
            if response_json:
                return _parse_json(text)
            return str(text).strip()
        except Exception as exc:  # noqa: BLE001 - network / API / rate limit failures
            self.last_error = str(exc)
            return None

    def status(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "last_error": self.last_error,
            "request_count": self.request_count,
        }

    # -------------------------------------------------------- 1. categorization

    def categorize(self, description, amount: float | None = None) -> str:
        result = self.generate(self._single_category_prompt(description, amount), response_json=True)
        if isinstance(result, dict):
            category = result.get("category")
            if category in CATEGORIES:
                return category
        return self._categorize_fallback(description, amount)

    def categorize_batch(self, transactions: list[dict]) -> list[dict]:
        if not transactions:
            return []
        records = [
            {
                "index": idx,
                "description": str(tx.get("description", "")),
                "amount": tx.get("amount"),
            }
            for idx, tx in enumerate(transactions)
        ]
        result = self.generate(
            _CATEGORY_PROMPT
            + "\nTransactions:\n"
            + json.dumps(records, default=str)
            + "\nReply with JSON only: [{\"index\": 0, \"category\": \"<category>\"}, ...]",
            response_json=True,
        )
        predicted: dict[int, str] = {}
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("category") in CATEGORIES:
                    predicted[int(item["index"])] = item["category"]
        categorized = []
        for idx, tx in enumerate(transactions):
            category = predicted.get(idx) or self._categorize_fallback(
                tx.get("description"), tx.get("amount")
            )
            categorized.append({**tx, "category": category})
        return categorized

    def apply_categories(self, transaction_service, transactions: list[dict]) -> dict:
        categorized = self.categorize_batch(transactions)
        processed = len(transactions)
        changed = 0
        for tx, categorized_tx in zip(transactions, categorized):
            if categorized_tx["category"] and categorized_tx["category"] != tx.get("category"):
                if transaction_service.update_category(tx["id"], categorized_tx["category"]):
                    changed += 1
        return {"processed": processed, "changed": changed, "source": self.provider}

    @staticmethod
    def _single_category_prompt(description, amount) -> str:
        line = f"{description}  (amount: {amount})" if amount is not None else str(description)
        return (
            _CATEGORY_PROMPT
            + f"\nTransaction: {line}"
            + "\nReply with JSON only: {\"category\": \"<one category>\"}"
        )

    def _categorize_fallback(self, description, amount: float | None) -> str:
        text = " ".join(str(description or "").lower().split())
        for category, keywords in _KEYWORD_RULES:
            if any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords):
                return category
        if amount is not None and amount > 0:
            return "Salary"
        return "Others"

    # ------------------------------------------------------- 2. savings advice

    def analyze_savings(self, transactions: pd.DataFrame) -> dict | None:
        base = self._analyze_savings_rules(transactions)
        if base is None:
            return None
        summary, ai_tips, source = self._savings_advice(transactions, base)
        base["summary"] = summary
        base["source"] = source
        for item in base["suggestions"]:
            category = item["category"]
            if category in ai_tips:
                item["title"], item["message"] = ai_tips[category]
        return base

    def _savings_advice(self, transactions, base) -> tuple[str, dict, str]:
        context = {
            "income": base["income"],
            "expense": base["expense"],
            "savings": base["savings"],
            "savings_rate": base["savings_rate"],
            "top_categories": [
                {"category": c, "spent": s}
                for c, s in list(base["category_spending"].items())[:5]
            ],
        }
        prompt = (
            "You are a personal finance advisor. Based on this month's finances, write a "
            "short, friendly summary (2-3 sentences) and up to 4 concrete savings "
            "suggestions, each with a short title and a 1-2 sentence message. "
            "Suggestions must reference the categories above.\n"
            "Context:\n"
            + json.dumps(context, default=str)
            + "\nReply with JSON only: {\"summary\": \"...\", "
            "\"suggestions\": [{\"category\": \"Food\", \"title\": \"...\", "
            "\"message\": \"...\"}]}"
        )
        result = self.generate(prompt, response_json=True)
        if not isinstance(result, dict):
            return self._savings_fallback(base), {}, "fallback"
        summary = str(result.get("summary", "")).strip()
        tips = {}
        for item in result.get("suggestions") or []:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", ""))
            if category in base["category_spending"]:
                title = str(item.get("title", "")).strip()
                message = str(item.get("message", "")).strip()
                if title and message:
                    tips[category] = (title, message)
        if not summary:
            return self._savings_fallback(base), tips, "gemini"
        return summary, tips, "gemini"

    @staticmethod
    def _savings_fallback(base) -> str:
        if base["income"] <= 0:
            return (
                f"No income was recorded. Expenses totalled ${base['expense']:,.2f} across "
                f"{len(base['category_spending'])} categories."
            )
        return (
            f"You earned ${base['income']:,.2f}, spent ${base['expense']:,.2f} and saved "
            f"${base['savings']:,.2f} ({base['savings_rate']:.1f}% of income). "
            f"{base['top_category']} was your biggest expense at ${base['top_amount']:,.2f}."
        )

    def _analyze_savings_rules(self, transactions) -> dict | None:
        if transactions is None or getattr(transactions, "empty", True):
            return None
        expenses = transactions.loc[transactions["amount"] < 0]
        if expenses.empty:
            return None
        expense_total = float(-expenses["amount"].sum())
        income_total = float(
            transactions.loc[transactions["amount"] > 0, "amount"].sum()
        )
        savings = round(income_total - expense_total, 2)
        savings_rate = round(savings / income_total * 100, 1) if income_total > 0 else 0.0

        by_category = (
            expenses.groupby("category")["amount"].sum().abs().sort_values(ascending=False)
        )
        category_spending = {str(key): float(value) for key, value in by_category.items()}
        top_category = str(by_category.index[0])
        top_amount = float(by_category.iloc[0])

        suggestions = []
        for category, spent in by_category.items():
            key = str(category)
            if key in SAVINGS_TIPS:
                factor = SAVINGS_FACTORS.get(key, 0.1)
                suggestions.append(
                    {
                        "category": key,
                        "title": SAVINGS_TIPS[key][0],
                        "message": SAVINGS_TIPS[key][1],
                        "spent": round(float(spent), 2),
                        "potential": round(float(spent) * factor, 2),
                    }
                )
        suggestions.sort(key=lambda item: item["potential"], reverse=True)

        unnecessary = []
        for category, spent in by_category.items():
            key = str(category)
            if key in DISCRETIONARY_CATEGORIES:
                factor = SAVINGS_FACTORS.get(key, 0.1)
                unnecessary.append(
                    {
                        "category": key,
                        "amount": round(float(spent), 2),
                        "potential": round(float(spent) * factor, 2),
                    }
                )
        unnecessary.sort(key=lambda item: item["amount"], reverse=True)

        additional_savings = round(sum(item["potential"] for item in suggestions), 2)
        return {
            "income": income_total,
            "expense": expense_total,
            "savings": savings,
            "savings_rate": savings_rate,
            "top_category": top_category,
            "top_amount": top_amount,
            "category_spending": category_spending,
            "suggestions": suggestions,
            "unnecessary": unnecessary,
            "additional_savings": additional_savings,
            "estimated_savings": round(savings + additional_savings, 2),
        }

    # --------------------------------------------------- 3. financial insights

    def generate_insights(self, transactions: pd.DataFrame) -> dict | None:
        if transactions is None or getattr(transactions, "empty", True):
            return None
        context = _transactions_context(transactions)
        prompt = (
            "You are a personal finance analyst. Write a short summary (2-3 sentences) "
            "of this month's financial health and 4-6 concise bullet insights. Base "
            "everything strictly on the numbers provided; never invent figures.\n"
            "Context:\n"
            + json.dumps(context, default=str)
            + "\nReply with JSON only: {\"summary\": \"...\", "
            "\"insights\": [\"...\", \"...\"]}"
        )
        result = self.generate(prompt, response_json=True)
        if isinstance(result, dict) and result.get("summary"):
            insights = [str(i) for i in (result.get("insights") or []) if str(i).strip()]
            return {
                "summary": str(result["summary"]).strip(),
                "insights": insights,
                "source": "gemini",
            }
        return self._insights_fallback(context)

    @staticmethod
    def _insights_fallback(context) -> dict:
        income = context["income"]
        expense = context["expense"]
        savings = income - expense
        rate = round(savings / income * 100, 1) if income > 0 else 0.0
        insights = [
            f"Total income was ${income:,.2f} across {context['income_tx']} transactions.",
            f"Total expenses were ${expense:,.2f} across {context['expense_tx']} transactions.",
        ]
        if context["top_categories"]:
            top = context["top_categories"][0]
            insights.append(
                f"{top['category']} was the largest expense category at ${top['amount']:,.2f} "
                f"({top['share']:.0f}% of spending)."
            )
        if income > 0:
            insights.append(f"Net savings were ${savings:,.2f} ({rate:.1f}% of income).")
        if context["discretionary_share"] >= 30:
            insights.append(
                "Discretionary categories (Food, Shopping, Entertainment, Travel) made up "
                f"{context['discretionary_share']:.0f}% of spending — the largest lever for "
                "short-term savings."
            )
        if context["largest_expense"] is not None:
            insights.append(
                f"The single largest expense was ${context['largest_expense']['amount']:,.2f} "
                f"({context['largest_expense']['description']})."
            )
        summary = (
            f"In this period you earned ${income:,.2f}, spent ${expense:,.2f} and "
            f"finished with a net of ${savings:,.2f}."
        )
        return {"summary": summary, "insights": insights, "source": "fallback"}

    # --------------------------------------------------- 4. monthly report summary

    def generate_report_summary(self, report: dict) -> dict:
        context = _report_context(report)
        prompt = (
            "You are a financial report writer. Write a concise, professional executive "
            "summary (3-4 sentences) of this monthly report, plus up to 3 highlights and "
            "up to 3 concerns. Base everything strictly on the numbers provided; never "
            "invent figures.\n"
            "Report data:\n"
            + json.dumps(context, default=str)
            + "\nReply with JSON only: {\"summary\": \"...\", "
            "\"highlights\": [\"...\"], \"concerns\": [\"...\"]}"
        )
        result = self.generate(prompt, response_json=True)
        if isinstance(result, dict) and result.get("summary"):
            return {
                "summary": str(result["summary"]).strip(),
                "highlights": [
                    str(i) for i in (result.get("highlights") or []) if str(i).strip()
                ],
                "concerns": [
                    str(i) for i in (result.get("concerns") or []) if str(i).strip()
                ],
                "source": "gemini",
            }
        return self._report_fallback(context)

    @staticmethod
    def _report_fallback(context) -> dict:
        summary = (
            f"{context['label']}: income of ${context['income']:,.2f} against expenses of "
            f"${context['expense']:,.2f} produced a net of ${context['savings']:,.2f} "
            f"({context['savings_rate']:.1f}% of income). "
        )
        if context["top_categories"]:
            top = context["top_categories"][0]
            summary += f"{top['category']} was the top expense at ${top['amount']:,.2f}. "
        if context["monthly_budget"]:
            remaining = context["monthly_budget"] - context["expense"]
            summary += (
                f"The monthly budget was ${context['monthly_budget']:,.2f}, leaving "
                f"${remaining:,.2f} unspent."
            )
        highlights = []
        concerns = []
        if context["savings"] > 0:
            highlights.append(
                f"Positive net savings of ${context['savings']:,.2f} this month."
            )
        else:
            concerns.append(
                f"Spending exceeded income by ${abs(context['savings']):,.2f} this month."
            )
        if context["bills_pending"] > 0:
            concerns.append(
                f"${context['bills_pending']:,.2f} in bills is still unpaid."
            )
        if context["investment_total"] > 0:
            highlights.append(
                f"Investments total ${context['investment_total']:,.2f}."
            )
        if context["overspent_categories"]:
            concerns.append(
                "Over-budget categories: "
                + ", ".join(context["overspent_categories"])
                + "."
            )
        return {
            "summary": summary.strip(),
            "highlights": highlights,
            "concerns": concerns,
            "source": "fallback",
        }


def _transactions_context(transactions: pd.DataFrame) -> dict:
    income_rows = transactions.loc[transactions["amount"] > 0]
    expense_rows = transactions.loc[transactions["amount"] < 0]
    income = float(income_rows["amount"].sum())
    expense = float(-expense_rows["amount"].sum())

    by_category = (
        expense_rows.groupby("category")["amount"].sum().abs().sort_values(ascending=False)
    )
    top_categories = []
    for key, value in by_category.items():
        top_categories.append(
            {
                "category": str(key),
                "amount": round(float(value), 2),
                "share": round(float(value) / expense * 100, 1) if expense else 0.0,
            }
        )

    discretionary = by_category[
        by_category.index.isin(DISCRETIONARY_CATEGORIES)
    ].sum()

    largest = None
    if not expense_rows.empty:
        row = expense_rows.loc[expense_rows["amount"].idxmin()]
        largest = {
            "description": str(row["description"]),
            "amount": round(float(-row["amount"]), 2),
        }

    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "income_tx": int(len(income_rows)),
        "expense_tx": int(len(expense_rows)),
        "top_categories": top_categories[:5],
        "discretionary_share": round(float(discretionary / expense * 100), 1)
        if expense
        else 0.0,
        "largest_expense": largest,
        "tx_count": int(len(transactions)),
    }


def _report_context(report: dict) -> dict:
    categories = report.get("categories")
    top_categories = []
    if categories is not None and not getattr(categories, "empty", True):
        for _, row in categories.head(5).iterrows():
            top_categories.append(
                {
                    "category": str(row["category"]),
                    "amount": round(float(row["amount"]), 2),
                }
            )

    overview = report.get("budget_overview")
    monthly_budget = report.get("monthly_budget")
    monthly_budget_amount = (
        float(monthly_budget["amount"]) if monthly_budget else None
    )
    overspent = []
    if overview is not None and not getattr(overview, "empty", True):
        overspent = [
            str(row["name"])
            for _, row in overview.iterrows()
            if row.get("overspent")
        ]

    return {
        "label": f"{report.get('start')} to {report.get('end')}",
        "income": round(float(report.get("income", 0)), 2),
        "expense": round(float(report.get("expense", 0)), 2),
        "savings": round(float(report.get("savings", 0)), 2),
        "savings_rate": float(report.get("savings_rate", 0)),
        "top_categories": top_categories,
        "monthly_budget": monthly_budget_amount,
        "bills_total": round(float(report.get("bills_total", 0)), 2),
        "bills_pending": round(float(report.get("bills_pending", 0)), 2),
        "investment_total": round(float(report.get("investment_total", 0)), 2),
        "overspent_categories": overspent,
    }
