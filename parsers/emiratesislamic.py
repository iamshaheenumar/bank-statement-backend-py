import re
from common.pdf_utils import open_pdf_safe, normalize_transactions, summarize_transactions, normalize_date

# Example: "14 AUG   12 AUG   RTA-ETISALAT DUBAI ARE   100.00"
LINE_REGEX = re.compile(
    r"^(\d{2}\s+[A-Z]{3})\s+(\d{2}\s+[A-Z]{3})\s+(.+?)\s+([\d,]+\.\d{2})(CR)?$",
    re.IGNORECASE,
)

SKIP_KEYWORDS = [
    "opening balance",
    "primary card no",
    "rewards summary",
    "cashback",
    "card limit",
    "minimum payment due",
    "payment due date",
    "profit/other charges",
    "current balance",
    "profit reversal",
    "finance charges",
]

def clean_amount(val: str) -> float:
    if not val:
        return 0.0
    v = val.replace(",", "").replace("CR", "").strip()
    try:
        return float(v)
    except ValueError:
        return 0.0

def parse_emiratesislamic(file_path: str, password: str | None = None):
    transactions = []
    pdf = open_pdf_safe(file_path, password)
    if isinstance(pdf, dict) and "error" in pdf:
        return pdf  # error dict

    with pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                raw = line.strip()
                if not raw:
                    continue

                low = raw.lower()
                if any(k in low for k in SKIP_KEYWORDS):
                    continue

                m = LINE_REGEX.match(raw)
                if not m:
                    continue

                post_date, txn_date, desc, amt_raw, cr = m.groups()
                amt_val = clean_amount(amt_raw)

                debit, credit = 0.0, 0.0
                if cr or "payment received" in desc.lower():
                    credit = amt_val
                else:
                    debit = amt_val

                transactions.append({
                    "transaction_date":  normalize_date(txn_date.strip(), "%d %b"),
                    "description": desc.strip(),
                    "debit": debit,
                    "credit": credit,
                    "amount": amt_val,
                    "bank": "Emirates Islamic",
                })

    normalized = normalize_transactions(transactions, "Emirates Islamic")
    return {
        "bank": "Emirates Islamic",
        "summary": summarize_transactions(normalized),
        "transactions": normalized,
    }
