from pathlib import Path

import pytest

from app.cli.fetch_source_document import fetch


def test_fetch_rejects_non_https_without_network_access(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        fetch("http://example.test/file.pdf", tmp_path / "file.pdf", "0" * 64)


def test_fetch_rejects_an_invalid_checksum_without_network_access(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        fetch("https://example.test/file.pdf", tmp_path / "file.pdf", "invalid")
