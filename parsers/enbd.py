import re
from common.pdf_utils import (
    open_pdf_safe,
    normalize_transactions,
    summarize_transactions,
    normalize_date,
)

# Common ENBD keywords
CREDIT_HINTS = {
    "salary", "credit", "inward", "uaefts", "refund", "reversal",
    "ipp customer credit", "sdm deposit", "deposit", "tt ref", "customer credit"
}

DATE_RE = re.compile(r"^(\d{2}[A-Z]{3}\d{2})(?:\s+(.*))?$")  # e.g. 03AUG25 [desc?]
AMOUNT_TAIL_RE = re.compile(
    r"(?<!\S)([\d,]+\.\d{2})(?:\s+)([\d,]+\.\d{2})\s*Cr\b", re.IGNORECASE
)
BALANCE_ONLY_CR_RE = re.compile(
    r"(?<!\S)([\d,]+\.\d{2})\s*Cr\b", re.IGNORECASE
)


# ---------- HELPERS ----------

def _clean_amount(s: str | None) -> float:
    if not s:
        return 0.0
    s = s.replace(",", "").replace("Cr", "").strip()
    if s in {"-", ""}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _looks_credit(desc: str) -> bool:
    d = desc.lower()
    # avoid false positive for "credit card payment"
    if "credit card payment" in d:
        return False
    return any(k in d for k in CREDIT_HINTS)


# ---------- MAIN PARSER ----------

def parse_enbd(file_path: str, password: str | None = None):
    """ENBD parser: fully text-based; determines debit/credit via balance comparison."""
    pdf = open_pdf_safe(file_path, password)
    if isinstance(pdf, dict) and "error" in pdf:
        return pdf

    transactions = []
    last_balance = None  # tracks previous balance

    with pdf:
        current: dict | None = None

        for page in pdf.pages:
            text = page.extract_text() or ""
            if not text.strip():
                continue

            for raw in text.splitlines():
                line = raw.strip()
                if not line:
                    continue

                # --- detect starting balance ---
                if "brought forward" in line.lower():
                    m_bal = re.search(r"([\d,]+\.\d{2})\s*Cr", line, re.IGNORECASE)
                    if m_bal:
                        last_balance = _clean_amount(m_bal.group(1))
                    continue

                # --- start of new transaction (date) ---
                m = DATE_RE.match(line)
                if m:
                    if current and current.get("balance") is not None:
                        transactions.append(current)

                    current = {
                        "transaction_date": normalize_date(m.group(1), "%d%b%y"),
                        "description": (m.group(2) or "").strip(),
                        "debit": 0.0,
                        "credit": 0.0,
                        "amount": 0.0,
                        "balance": None,
                        "bank": "ENBD",
                    }
                    continue

                # --- inside transaction block ---
                if current:
                    # detect line with amount + balance
                    mt = AMOUNT_TAIL_RE.search(line)
                    if mt:
                        amt_val = _clean_amount(mt.group(1))
                        bal_val = _clean_amount(mt.group(2))
                        current["amount"] = amt_val
                        current["balance"] = bal_val

                        # Determine debit/credit by balance change
                        if last_balance is not None:
                            if bal_val > last_balance:
                                current["credit"] = amt_val
                            elif bal_val < last_balance:
                                current["debit"] = amt_val
                            else:
                                # same balance → fallback to hint
                                if _looks_credit(current["description"]):
                                    current["credit"] = amt_val
                                else:
                                    current["debit"] = amt_val
                        else:
                            # first record (no previous balance) → still try hint
                            if _looks_credit(current["description"]):
                                current["credit"] = amt_val
                            else:
                                current["debit"] = amt_val

                        last_balance = bal_val
                        transactions.append(current)
                        current = None
                        continue

                    # detect balance-only line (rare)
                    mb = BALANCE_ONLY_CR_RE.search(line)
                    if mb:
                        bal_val = _clean_amount(mb.group(1))
                        current["balance"] = bal_val
                        last_balance = bal_val
                        transactions.append(current)
                        current = None
                        continue

                    # accumulate description lines
                    low = line.lower()
                    if "brought forward" in low or "carried forward" in low:
                        continue
                    if current["description"]:
                        current["description"] += " " + line
                    else:
                        current["description"] = line

        # final flush
        if current and current.get("balance") is not None:
            transactions.append(current)

    # filter out carry/brought forward
    clean = [
        t for t in transactions
        if t["transaction_date"]
        and t["description"]
        and not any(x in t["description"].lower() for x in ("brought forward", "carried forward"))
    ]

    normalized = normalize_transactions(clean, "ENBD")
    return {
        "bank": "ENBD",
        "summary": summarize_transactions(normalized),
        "transactions": normalized,
    }
