import datetime as dt
import re

import pandas as pd

DATE_WORDS = [
    "date",
    "posted",
    "posting",
    "transaction date",
    "value date",
    "booking",
    "settlement date",
]
AMOUNT_WORDS = ["amount", "amt", "value"]
DESC_WORDS = [
    "description",
    "details",
    "narrative",
    "merchant",
    "payee",
    "particulars",
    "reference",
    "memo",
    "transaction",
    "narration",
    "counterparty",
    "comments",
]
DEBIT_WORDS = ["withdrawal", "withdraw", "debit", "money out", "paid out", "paidout", "outflow"]
CREDIT_WORDS = ["deposit", "credit", "money in", "paid in", "paidin", "inflow"]
BALANCE_WORDS = ["balance", "bal", "new balance"]

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%d.%m.%Y",
    "%m.%d.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d-%b-%Y",
    "%d/%m/%y",
    "%m/%d/%y",
    "%d-%m-%y",
]


def parse_amount(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if pd.isna(value):
            return None
        return float(value)
    if isinstance(value, (dt.datetime, dt.date, pd.Timestamp)):
        return None
    text = str(value).strip().replace("\u00a0", " ")
    text = re.sub(r"[$€£\s]", "", text)
    text = text.replace("USD", "").replace("EUR", "").replace("GBP", "")
    if not text or text in ("-", "--", "—", "–", "nil", "N/A", "n/a"):
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    lower = text.lower()
    if lower.endswith("cr"):
        text = text[:-2]
    elif lower.endswith("dr"):
        negative = True
        text = text[:-2]
    elif lower.endswith(" d") or lower.endswith(" c"):
        pass
    if text.startswith("-"):
        negative = True
        text = text[1:]
    if text.startswith("+"):
        text = text[1:]
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", "")
    try:
        value = float(text)
    except ValueError:
        return None
    if value < 0:
        negative = True
        value = abs(value)
    return -value if negative else value


def parse_date(value) -> dt.date | None:
    if isinstance(value, pd.Timestamp):
        if pd.isna(value):
            return None
        return value.date()
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, (int, float)):
        try:
            return dt.datetime(1899, 12, 30) + dt.timedelta(days=float(value))
        except (ValueError, OverflowError, OSError):
            return None
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in ("nan", "nat", "none", "n/a"):
        return None
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    ts = pd.to_datetime(text, errors="coerce")
    if pd.isna(ts):
        return None
    return ts.date()


def _normalise(value) -> str:
    return str(value).strip().lower().replace("_", " ").replace("-", " ")


def _pick_column(frame: pd.DataFrame, words: list[str]) -> str | None:
    for column in frame.columns:
        col = _normalise(column)
        for word in words:
            if word in col:
                return column
    return None


def _clean_description(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value)
    if text.lower() in ("nan", "nat", "none"):
        return ""
    return " ".join(text.split())


def _find_header_row(raw: pd.DataFrame) -> int:
    limit = min(len(raw), 12)
    for index in range(limit):
        columns = [_normalise(c) for c in raw.iloc[index].tolist()]
        joined = " ".join(columns)
        has_date = any(any(w in c for w in DATE_WORDS) for c in columns)
        has_amount = any(
            any(w in c for w in AMOUNT_WORDS) or any(w in c for w in DEBIT_WORDS) or any(w in c for w in CREDIT_WORDS)
            for c in columns
        )
        if has_date and has_amount:
            return index
    return 0


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [_normalise(c) for c in frame.columns]
    date_col = _pick_column(frame, DATE_WORDS)
    excluded = {date_col} if date_col else set()

    def pick(words: list[str]) -> str | None:
        for column in frame.columns:
            if column in excluded:
                continue
            col = _normalise(column)
            if any(word in col for word in words):
                return column
        return None

    amount_col = pick(AMOUNT_WORDS)
    if amount_col:
        excluded.add(amount_col)
    debit_col = pick(DEBIT_WORDS)
    if debit_col:
        excluded.add(debit_col)
    credit_col = pick(CREDIT_WORDS)
    if credit_col:
        excluded.add(credit_col)
    balance_col = pick(BALANCE_WORDS)
    if balance_col:
        excluded.add(balance_col)
    desc_col = pick(DESC_WORDS)

    rows = []
    for _, row in frame.iterrows():
        date_value = parse_date(row[date_col]) if date_col is not None else None
        description = _clean_description(row[desc_col]) if desc_col is not None else ""
        if amount_col is not None:
            amount = parse_amount(row[amount_col])
        elif debit_col is not None or credit_col is not None:
            debit = parse_amount(row[debit_col]) if debit_col is not None else None
            credit = parse_amount(row[credit_col]) if credit_col is not None else None
            debit = abs(debit) if debit is not None else 0.0
            credit = abs(credit) if credit is not None else 0.0
            amount = credit - debit
        else:
            amount = None
        balance = parse_amount(row[balance_col]) if balance_col is not None else None
        rows.append(
            {
                "date": date_value,
                "description": description,
                "amount": amount,
                "balance": balance,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result = result[result["date"].notna() & result["amount"].notna()].copy()
    result["description"] = result["description"].fillna("").astype(str)
    result["date"] = pd.to_datetime(result["date"]).dt.date
    result["amount"] = pd.to_numeric(result["amount"], errors="coerce")
    result = result.dropna(subset=["amount"])
    return result.reset_index(drop=True)


def extract_transactions_from_excel(file_or_path, sheet_name: str | None = None) -> pd.DataFrame:
    name = getattr(file_or_path, "name", None) or str(file_or_path)
    if str(name).lower().endswith(".csv"):
        raw = pd.read_csv(file_or_path, header=None)
    elif sheet_name is not None:
        raw = pd.read_excel(file_or_path, header=None, sheet_name=sheet_name)
    else:
        raw = pd.read_excel(file_or_path, header=None)

    if raw.empty:
        return pd.DataFrame(columns=["date", "description", "amount", "balance"])

    header_index = _find_header_row(raw)
    frame = raw.iloc[header_index + 1:].reset_index(drop=True)
    if frame.empty:
        return pd.DataFrame(columns=["date", "description", "amount", "balance"])
    frame.columns = [str(c) for c in raw.iloc[header_index].tolist()]
    return normalize_frame(frame)
