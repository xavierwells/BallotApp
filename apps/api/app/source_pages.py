"""PDF navigation metadata, separate from immutable printed-page citations."""

import re


# Verified against the retained bytes, including every pilot county source page.
# The Texas SOS report has one unnumbered cover, then printed pages 1–1395.
# Key by exact content, never publisher/URL: replacement PDFs may paginate differently.
_PRINTED_PAGE_LAYOUTS = {
    "c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c": (1, 1395),
}


def pdf_page_number(checksum: str, source_page: str) -> int | None:
    """Return a one-based viewer index; do not reinterpret nonnumeric citations.

    Numeric citations in other documents keep the existing same-number behavior.
    Add a checksum-specific layout only after checking the actual document.
    """
    if not re.fullmatch(r"[1-9][0-9]{0,6}", source_page):
        return None
    printed = int(source_page)
    offset, last_printed_page = _PRINTED_PAGE_LAYOUTS.get(checksum, (0, None))
    if last_printed_page is not None and printed > last_printed_page:
        return None
    return printed + offset
