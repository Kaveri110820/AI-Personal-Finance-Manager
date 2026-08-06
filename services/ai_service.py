import re

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
