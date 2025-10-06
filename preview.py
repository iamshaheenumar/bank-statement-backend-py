# preview.py
import pdfplumber

def _split_cell(x):
    """Return both the raw cell and a split-by-newline version."""
    raw = "" if x is None else str(x)
    parts = [p.strip() for p in raw.split("\n") if p and p.strip()]
    return {"raw": raw, "split": parts}

def preview_pdf(file_path: str, password: str | None = None):
    """
    Generic PDF preview:
    - Returns text lines per page
    - Returns all tables per page, with raw and split cells
    - No bank-specific logic
    """
    result = {"text_by_page": [], "tables_by_page": []}

    with pdfplumber.open(file_path, password=password) as pdf:
        # Text mode
        for pidx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = [{"i": i, "line": ln} for i, ln in enumerate(text.splitlines(), start=1)]
            result["text_by_page"].append({"page": pidx, "lines": lines})

        # Table mode
        for pidx, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            page_tables = []
            for tidx, tbl in enumerate(tables, start=1):
                norm_rows = []
                for ridx, row in enumerate(tbl or [], start=1):
                    norm_row = [_split_cell(c) for c in (row or [])]
                    norm_rows.append({"row_index": ridx, "cells": norm_row})
                page_tables.append({"table_index": tidx, "rows": norm_rows})
            result["tables_by_page"].append({"page": pidx, "tables": page_tables})

    return result
