import re
from common.pdf_utils import open_pdf_safe, normalize_transactions, summarize_transactions, normalize_date

def classify_transaction(desc: str, amount: float):
    desc_lower = desc.lower()
    credit_keywords = [
        "inward", "credit", "uaefts", "payment received",
        "refund", "reversal", "salary"
    ]
    for kw in credit_keywords:
        if kw in desc_lower:
            return 0.0, amount
    return amount, 0.0

ROW_PATTERN = re.compile(
    r"(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+(\d{1,3}(?:,\d{3})*\.\d{2})(?:\s|-)"
)

def parse_mashreq(file_path: str, password: str | None = None):
    transactions = []
    pdf = open_pdf_safe(file_path, password)
    if isinstance(pdf, dict) and "error" in pdf:
        return pdf

    with pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for match in ROW_PATTERN.finditer(text):
                t_date, p_date, desc, amount = match.groups()
                value = float(amount.replace(",", ""))
                debit, credit = classify_transaction(desc, value)

                transactions.append({
                    "transaction_date": normalize_date(t_date, "%d/%m"),  # unify naming
                    "posting_date": normalize_date(p_date, "%d/%m"),      # kept for internal use but will be dropped in normalization
                    "description": desc.strip(),
                    "debit": debit,
                    "credit": credit,
                    "amount": value,         # unify with other parsers
                    "bank": "Mashreq",
                })

    normalized = normalize_transactions(transactions, "Mashreq")
    return {
        "bank": "Mashreq",
        "summary": summarize_transactions(normalized),
        "transactions": normalized,
    }
