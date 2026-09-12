from copy import deepcopy

import pytest

from app.editorial_review import content_hash, race_reviews
from app.source_pages import pdf_page_number


CERTIFICATION = "c13ffb4ebeee389fa9818d47b31f77b4e260ea6e6f5389cb7bf0f36d9b44d87c"


@pytest.mark.parametrize("printed", [*range(70, 76), *range(271, 276), *range(783, 788)])
def test_pilot_citations_skip_the_unnumbered_cover(printed):
    assert pdf_page_number(CERTIFICATION, str(printed)) == printed + 1


def test_offset_does_not_apply_to_other_or_replaced_documents():
    assert pdf_page_number("0" * 64, "271") == 271
    assert pdf_page_number(CERTIFICATION, "1") == 2
    assert pdf_page_number(CERTIFICATION, "1395") == 1396
    assert pdf_page_number(CERTIFICATION, "1396") is None


@pytest.mark.parametrize("citation", ["", "0", "-1", "271–275", "Appendix A", "1.5"])
def test_non_page_citations_require_manual_navigation(citation):
    assert pdf_page_number(CERTIFICATION, citation) is None


def test_navigation_metadata_does_not_change_the_reviewed_manifest():
    class NoDecisions:
        def execute(self, *_args, **_kwargs):
            return self

        def mappings(self):
            return self

        def all(self):
            return []

    manifest = {"races": [{"key": "synthetic", "sourcePage": "271"}]}
    original = deepcopy(manifest)
    digest = content_hash(manifest)
    batch = {"id": "synthetic", "publication_id": "synthetic", "document_id": "synthetic",
             "manifest": manifest, "checksum_sha256": CERTIFICATION, "required_reviewers": 1}
    result = race_reviews(NoDecisions(), batch)
    assert result[0]["sourcePage"] == "271"
    assert result[0]["pdfPageNumber"] == 272
    assert result[0]["reviewStatus"] == "unreviewed"
    assert manifest == original
    assert content_hash(manifest) == digest
