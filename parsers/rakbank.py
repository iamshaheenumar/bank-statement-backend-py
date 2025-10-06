import re
import pdfplumber
from common.pdf_utils import open_pdf_safe, normalize_transactions, summarize_transactions, normalize_date

# AED transaction
RAKBANK_LINE_REGEX = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+AED\s+([\d,]+\.\d{2})(?:\s*(?:CR|Cr))?\s+-\s+([\d,]+\.\d{2})(?:\s*(?:CR|Cr))?$",
    re.IGNORECASE,
)

# FX transaction
RAKBANK_FX_REGEX = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+([A-Z]{3})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})(?:\s*(CR|Cr))?$",
    re.IGNORECASE,
)

SKIP_KEYWORDS = [
    "opening balance",
    "closing balance",
    "available credit",
    "minimum payment due",
    "payment due date",
    "credit limit",
]

DROP_HINTS = (
    "your credit card statement",
    "statement period",
    "product name",
    "card number",
    "page[",
)

def clean_amount(val: str | None) -> float:
    if not val:
        return 0.0
    return float(val.replace(",", "").replace("CR", "").replace("Cr", "").strip())

def parse_rakbank(file_path: str, password: str | None = None):
    transactions = []
    pdf = open_pdf_safe(file_path, password)
    if isinstance(pdf, dict) and "error" in pdf:
        return pdf  # error dict

    with pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

            buffer_desc = []

            for raw in lines:
                low = raw.lower()
                if any(k in low for k in SKIP_KEYWORDS):
                    continue

                # --------- AED transaction ----------
                m = RAKBANK_LINE_REGEX.match(raw)
                if m:
                    date, desc, amt_raw, balance_raw = m.groups()
                    if any(h in " ".join(buffer_desc).lower() for h in DROP_HINTS):
                        buffer_desc = []

                    full_desc = " ".join(buffer_desc + [desc.strip()]).strip()
                    buffer_desc = []  # clear

                    amt_val = clean_amount(amt_raw)
                    balance_val = clean_amount(balance_raw)

                    debit, credit = 0.0, 0.0
                    if "cr" in raw.lower() or "payment" in full_desc.lower() or "refund" in full_desc.lower():
                        credit = amt_val
                    else:
                        debit = amt_val

                    transactions.append({
                        "transaction_date": normalize_date(date, "%d/%m/%Y"),
                        "description": full_desc,
                        "debit": debit,
                        "credit": credit,
                        "amount": amt_val,
                        "balance": balance_val,
                        "bank": "RAKBANK",
                    })
                    continue

                # --------- FX transaction ----------
                mfx = RAKBANK_FX_REGEX.match(raw)
                if mfx:
                    date, ccy, fx_amt, fx_rate, aed_amt, cr_flag = mfx.groups()
                    if any(h in " ".join(buffer_desc).lower() for h in DROP_HINTS):
                        buffer_desc = []

                    full_desc = " ".join(buffer_desc).strip()
                    buffer_desc = []  # clear

                    fx_amt_val = clean_amount(fx_amt)
                    fx_rate_val = clean_amount(fx_rate)
                    aed_val = clean_amount(aed_amt)

                    debit, credit = 0.0, 0.0
                    if cr_flag or "cr" in raw.lower() or "payment" in full_desc.lower() or "refund" in full_desc.lower():
                        credit = aed_val
                    else:
                        debit = aed_val

                    transactions.append({
                        "transaction_date": normalize_date(date, "%d/%m/%Y"),
                        "description": full_desc,
                        "debit": debit,
                        "credit": credit,
                        "amount": aed_val,
                        "bank": "RAKBANK",
                        # extra FX info (ignored in normalized output)
                        "fx_currency": ccy,
                        "fx_amount": fx_amt_val,
                        "fx_rate": fx_rate_val,
                    })
                    continue

                # ---------- Non-transaction line ----------
                buffer_desc.append(raw)
    normalized = normalize_transactions(transactions, "RAKBANK")
    return {
        "bank": "RAKBANK",
        "summary": summarize_transactions(normalized),
        "transactions": normalized,
    }