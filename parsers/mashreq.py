import re
import datetime
import calendar
from common.pdf_utils import open_pdf_safe, normalize_transactions, summarize_transactions, normalize_date

BANK_NAME = "Mashreq"
CARD_TYPE = "credit"

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

            # scan lines for a 'Statement date' which represents to_date
            for raw in text.splitlines():
                line = (raw or "").strip()
                if not line:
                    continue
                low = line.lower()
                if "statement date" in low:
                    # permissive date finder (dd/mm/YYYY)
                    m = re.search(r"(\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4})", line)
                    if m:
                        found = m.group(1).replace(" ", "")
                        # normalize to ISO
                        td = normalize_date(found, "%d/%m/%Y")
                        if td:
                            # compute from_date as one month before td
                            try:
                                td_dt = datetime.datetime.strptime(td, "%Y-%m-%d").date()
                                # subtract one month
                                if td_dt.month == 1:
                                    fy = td_dt.year - 1
                                    fm = 12
                                else:
                                    fy = td_dt.year
                                    fm = td_dt.month - 1
                                # clamp day to last day of prev month
                                last_day = calendar.monthrange(fy, fm)[1]
                                fd_day = min(td_dt.day, last_day)
                                fd_dt = datetime.date(fy, fm, fd_day)
                                statement_to = td
                                statement_from = fd_dt.isoformat()
                            except Exception:
                                # ignore failures and leave as None
                                pass
                    # don't break; there might be multiple pages/lines — continue scanning

            for match in ROW_PATTERN.finditer(text):
                t_date, p_date, desc, amount = match.groups()
                value = float(amount.replace(",", ""))
                debit, credit = classify_transaction(desc, value)

                # parse day/month then apply year from statement dates if available
                txn_iso = normalize_date(t_date, "%d/%m")
                try:
                    # If normalize_date returned an ISO with a filled year, parse it
                    txn_dt = datetime.datetime.strptime(txn_iso, "%Y-%m-%d")
                except Exception:
                    # fallback: parse day/month and use current year
                    txn_dt = datetime.datetime.strptime(t_date, "%d/%m")

                if statement_from and statement_to:
                    from_year = int(statement_from[:4])
                    to_year = int(statement_to[:4])
                    # apply to_year then handle year rollover similar to other parsers
                    txn_dt = txn_dt.replace(year=to_year)
                    statement_to_dt = datetime.datetime.strptime(statement_to, "%Y-%m-%d")
                    if statement_to_dt.month < 6 and txn_dt.month > 6:
                        txn_dt = txn_dt.replace(year=from_year)
                else:
                    # ensure year is set (normalize_date may have filled it already)
                    if txn_dt.year == 1900:
                        txn_dt = txn_dt.replace(year=datetime.datetime.now().year)

                transactions.append({
                    "transaction_date": txn_dt.date().isoformat(),  # unify naming (YYYY-MM-DD)
                    "description": desc.strip(),
                    "debit": debit,
                    "credit": credit,
                    "amount": value,         # unify with other parsers
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
