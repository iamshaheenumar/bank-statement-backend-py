from common.pdf_utils import open_pdf_safe

BANK_KEYWORDS = {
    "mashreq": ["mashreq", "mashreqbank"],
    "enbd": ["emirates nbd", "dubai bank"],
    "adcb": ["adcb", "abu dhabi commercial bank"],
    "emiratesislamic": ["emirates islamic"],
    "rakbank": ["rakbank", "national bank of ras al khaimah"],
    # add more banks as needed
}

def detect_bank(file_path: str, password: str | None = None) -> str | None:
    pdf = open_pdf_safe(file_path, password)
    if isinstance(pdf, dict) and "error" in pdf:
        return None  # can't detect if password is wrong or file is invalid

    with pdf:
        # Check first 2 pages (some banks show logos/headers differently)
        pages_to_check = pdf.pages[:2] if len(pdf.pages) >= 2 else pdf.pages
        for page in pages_to_check:
            text = (page.extract_text() or "").lower()
            for bank, keywords in BANK_KEYWORDS.items():
                if any(kw in text for kw in keywords):
                    return bank

    return None
