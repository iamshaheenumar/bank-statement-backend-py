from common.pdf_utils import open_pdf_safe, normalize_transactions, normalize_date, summarize_transactions

BANK_NAME = "unknown"
CARD_TYPE = "debit"

def parse_generic(file_path: str, password: str | None = None):
    """
    Generic fallback parser:
    Extracts raw lines containing digits (crude heuristic).
    Normalizes structure to match other bank parsers.
    """
    transactions = []
    statement_from = None
    statement_to = None
    pdf = open_pdf_safe(file_path, password)
    if isinstance(pdf, dict) and "error" in pdf:
        return pdf

    with pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.splitlines():
                raw = line.strip()
                if not raw:
                    continue

                # crude filter: lines that contain any number
                if any(c.isdigit() for c in raw):
                    # try to normalize a date if one appears at start
                    parts = raw.split(maxsplit=1)
                    possible_date = parts[0] if parts else ""
                    normalized_date = normalize_date(possible_date)

                    transactions.append({
                        "transaction_date": normalized_date,
                        "description": raw,
                        "debit": 0.0,
                        "credit": 0.0,
                        "amount": 0.0,
                        "balance": None,
                        "bank": BANK_NAME,
                        "card_type": CARD_TYPE,
                    })

    normalized = normalize_transactions(transactions, BANK_NAME, CARD_TYPE)
    return {
        "bank": BANK_NAME,
        "card_type": CARD_TYPE,
        "summary": summarize_transactions(normalized),
        "transactions": normalized,
        "from_date": statement_from,
        "to_date": statement_to,
    }
