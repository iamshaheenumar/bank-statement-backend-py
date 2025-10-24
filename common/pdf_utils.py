import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from datetime import datetime

def normalize_date(raw_date: str, fmt: str | None = None) -> str:
    """
    Normalize a date string into ISO format YYYY-MM-DD.
    If fmt is provided, it tries that format first.
    If fmt is None or parsing fails, returns ''.
    """
    if not raw_date:
        return ""

    raw = raw_date.strip().upper().replace(".", "").replace(",", "")

    # If explicit format is known, use it directly
    if fmt:
        try:
            dt = datetime.strptime(raw, fmt)
            # Fill missing year (for 15/08, 14 AUG)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return ""

    # Optional fallback formats for generic parsing
    fallback_patterns = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%d/%m",
        "%d %b %Y",
        "%d %b",
        "%d%b%y",
        "%d%b%Y",
    ]

    for p in fallback_patterns:
        try:
            dt = datetime.strptime(raw, p)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return ""

def open_pdf_safe(file_path: str, password: str | None = None):
    """Open a PDF with proper error handling for wrong password."""
    try:
        return pdfplumber.open(file_path, password=password)
    except PDFPasswordIncorrect:
        return {"error": "Invalid password for PDF"}
    except Exception as e:
        return {"error": f"Failed to open PDF: {str(e)}"}

def normalize_transactions(transactions: list, bank: str, card_type:str):
    """Ensure all transactions return the same structure."""
    normalized = []
    for tx in transactions:
        normalized.append({
            "transaction_date": tx.get("transaction_date", ""),
            "description": tx.get("description", ""),
            "debit": tx.get("debit", 0.0),
            "credit": tx.get("credit", 0.0),
            "amount": tx.get("amount", 0.0),
            "bank": bank,
            "card_type": card_type
        })
    return normalized

def summarize_transactions(transactions: list[dict]) -> dict:
    """Return summary stats for a list of transactions."""
    record_count = len(transactions)
    total_debit = sum(t.get("debit", 0.0) for t in transactions)
    total_credit = sum(t.get("credit", 0.0) for t in transactions)
    net_change = total_credit - total_debit

    return {
        "record_count": record_count,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "net_change": net_change,
    }


