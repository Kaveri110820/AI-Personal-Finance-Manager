import re

import pandas as pd

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


class AIService:
    def __init__(self, provider: str = "placeholder", model: str | None = None):
        self.provider = provider
        self.model = model or "placeholder-rule-based"

    def categorize(self, description, amount: float | None = None) -> str:
        if self.provider != "placeholder":
            raise NotImplementedError("Only the placeholder provider is available yet.")
        return self._categorize_placeholder(description, amount)

    def categorize_batch(self, transactions: list[dict]) -> list[dict]:
        categorized = []
        for transaction in transactions:
            category = self.categorize(
                transaction.get("description"),
                transaction.get("amount"),
            )
            categorized.append({**transaction, "category": category})
        return categorized

    def apply_categories(self, transaction_service, transactions: list[dict]) -> dict:
        processed = 0
        changed = 0
        for transaction in transactions:
            processed += 1
            suggested = self.categorize(
                transaction.get("description"),
                transaction.get("amount"),
            )
            if suggested and suggested != transaction.get("category"):
                if transaction_service.update_category(transaction["id"], suggested):
                    changed += 1
        return {"processed": processed, "changed": changed}

    def _categorize_placeholder(self, description, amount: float | None) -> str:
        text = " ".join(str(description or "").lower().split())
        for category, keywords in _KEYWORD_RULES:
            if any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords):
                return category
        if amount is not None and amount > 0:
            return "Salary"
        return "Others"

    def analyze_savings(self, transactions: pd.DataFrame) -> dict | None:
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
