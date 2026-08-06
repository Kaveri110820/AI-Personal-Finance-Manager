import re

import pdfplumber

from utils.excel_reader import parse_amount, parse_date

DATE_RE = re.compile(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}")
DATE_TEXT_RE = re.compile(
    r"(?:\d{1,2}\s)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}",
    re.IGNORECASE,
)
AMOUNT_CLEAN_RE = re.compile(r"[0-9.,()$€£\-− ]")


def _is_amount_cell(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if AMOUNT_CLEAN_RE.sub("", text):
        return False
    digits = re.sub(r"[^0-9]", "", text)
    return 1 <= len(digits) <= 12


def _find_date_cell(cells: list[str]):
    for cell in cells:
        if DATE_RE.search(cell) or DATE_TEXT_RE.search(cell):
            return cell
    return None


def _header_roles(cells: list[str]) -> dict[str, int]:
    roles: dict[str, int] = {}
    for index, cell in enumerate(cells):
        col = cell.strip().lower()
        if any(w in col for w in ("transaction date", "posting date", "date")):
            roles["date"] = index
        if any(w in col for w in ("withdrawal", "withdraw", "debit", "money out", "paid out", "outflow")):
            roles["debit"] = index
        if any(w in col for w in ("deposit", "credit", "money in", "paid in", "inflow")):
            roles["credit"] = index
        if "balance" in col:
            roles["balance"] = index
        if ("amount" in col or "value" in col) and "balance" not in col:
            roles["amount"] = index
    if "date" in roles and any(role in roles for role in ("debit", "credit", "amount")):
        return roles
    return {}


def _clean_description(parts: list[str]) -> str:
    return " ".join(p.strip() for p in parts if p and p.strip()).strip()


def _parse_row_with_schema(cells: list[str], schema: dict[str, int]):
    date_index = schema.get("date")
    if date_index is None or date_index >= len(cells):
        return None
    date_value = parse_date(cells[date_index])
    if date_value is None:
        return None

    role_indexes = set(schema.values())
    description = _clean_description(
        [cells[i] for i in range(len(cells)) if i not in role_indexes and cells[i]]
    )
    if not description:
        description = "Statement entry"

    debit = parse_amount(cells[schema["debit"]]) if "debit" in schema and schema["debit"] < len(cells) else None
    credit = parse_amount(cells[schema["credit"]]) if "credit" in schema and schema["credit"] < len(cells) else None
    amount = parse_amount(cells[schema["amount"]]) if "amount" in schema and schema["amount"] < len(cells) else None
    balance = parse_amount(cells[schema["balance"]]) if "balance" in schema and schema["balance"] < len(cells) else None

    if amount is None and (debit is not None or credit is not None):
        amount = (credit if credit is not None else 0.0) - (abs(debit) if debit is not None else 0.0)
    if amount is None or amount == 0:
        return None
    return {"date": date_value, "description": description, "amount": amount, "balance": balance}


def _parse_row_heuristic(cells: list[str]):
    date_cell = _find_date_cell(cells)
    if not date_cell:
        return None
    date_value = parse_date(date_cell)
    if date_value is None:
        return None

    date_index = cells.index(date_cell)
    amount_cells = [
        (index, cell) for index, cell in enumerate(cells) if index != date_index and _is_amount_cell(cell)
    ]
    description_parts = [
        cell for index, cell in enumerate(cells) if index != date_index and not _is_amount_cell(cell)
    ]
    description = _clean_description(description_parts)
    if not description:
        description = "Statement entry"

    amounts = [parse_amount(cell) for _, cell in amount_cells]
    amounts = [value for value in amounts if value is not None]
    if not amounts:
        return None
    if len(amounts) == 1:
        amount, balance = amounts[0], None
    elif len(amounts) == 2:
        amount, balance = amounts[0], amounts[1]
    else:
        amount, balance = amounts[0], amounts[-1]
    if amount == 0:
        return None
    return {"date": date_value, "description": description, "amount": amount, "balance": balance}


def _parse_table(table_rows: list[list[str | None]]) -> list[dict]:
    rows: list[dict] = []
    schema: dict[str, int] = {}
    for raw_row in table_rows:
        cells = [str(cell).strip() if cell is not None else "" for cell in raw_row]
        if not any(cells):
            continue
        if not schema:
            schema = _header_roles(cells)
            if schema:
                continue
            parsed = _parse_row_heuristic(cells)
            if parsed:
                rows.append(parsed)
            continue
        parsed = _parse_row_with_schema(cells, schema)
        if parsed:
            rows.append(parsed)
    return rows


def _parse_text_line(text: str):
    match = DATE_RE.search(text) or DATE_TEXT_RE.search(text)
    if not match:
        return None
    date_value = parse_date(match.group(0))
    if date_value is None:
        return None
    head, _, tail = text.partition(match.group(0))
    tokens = tail.split()
    amount_tokens = []
    description_tokens = []
    for token in tokens:
        if _is_amount_cell(token):
            amount_tokens.append(token)
        else:
            description_tokens.append(token)
    description = _clean_description([head] + description_tokens)
    if not description:
        description = "Statement entry"
    if not amount_tokens:
        return None
    amounts = [parse_amount(token) for token in amount_tokens]
    amounts = [value for value in amounts if value is not None]
    if not amounts:
        return None
    amount = amounts[0]
    balance = amounts[-1] if len(amounts) >= 2 else None
    if amount == 0:
        return None
    return {"date": date_value, "description": description, "amount": amount, "balance": balance}


def extract_transactions_from_pdf(file_or_path) -> list[dict]:
    rows: list[dict] = []
    with pdfplumber.open(file_or_path) as pdf:
        for page in pdf.pages:
            table_rows = []
            for table in page.extract_tables():
                table_rows.extend(table)
            if table_rows:
                rows.extend(_parse_table(table_rows))
            else:
                for line in page.extract_text_lines():
                    parsed = _parse_text_line(line.get("text", ""))
                    if parsed:
                        rows.append(parsed)
    return rows
