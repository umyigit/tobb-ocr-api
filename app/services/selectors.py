"""HTML CSS selectors for TOBB website parsing.

Centralized here so that when TOBB changes their markup,
only this file needs updating.
"""

from __future__ import annotations

# Unvan sorgulama (public search) result selectors
SEARCH_RESULT_TABLE = "table.table.table-bordered.table-striped"
SEARCH_RESULT_ROW = "tbody tr"
SEARCH_TOTAL_HEADER = "thead th[colspan]"

# Ilan goruntuleme (authenticated gazette search) result selectors
ILAN_RESULT_TABLE = "#tblIlanGoruntuleme"
ILAN_RESULT_ROW = "tbody tr"
ILAN_TOTAL_SPAN = "span"  # "Yayinlanmis ... Ilanlari (92 Adet)"
ILAN_PDF_LINK = 'a[href*="pdf_goster"]'

# PDF viewer selectors (pdf_goster.php may return HTML with embedded PDF)
GAZETTE_PDF_EMBED = "embed[src*='.pdf']"
GAZETTE_PDF_IFRAME = "iframe[src*='.pdf']"
GAZETTE_PDF_OBJECT = "object[data*='.pdf']"
