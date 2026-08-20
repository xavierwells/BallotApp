import hashlib

import pytest

from app.document_storage import DocumentStorageError, FilesystemDocumentStore


def test_filesystem_store_retains_content_by_checksum_without_overwriting(tmp_path) -> None:
    store = FilesystemDocumentStore(tmp_path)
    content = b"official sample ballot\n"

    first = store.put_bytes(content)
    second = store.put_bytes(content)

    assert first == second
    assert first.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert first.storage_key == f"sha256/{first.checksum_sha256[:2]}/{first.checksum_sha256}"
    assert store.read_bytes(first.storage_key) == content


def test_filesystem_store_rejects_invalid_or_tampered_artifacts(tmp_path) -> None:
    store = FilesystemDocumentStore(tmp_path)
    stored = store.put_bytes(b"notice")
    location = tmp_path / stored.storage_key
    location.write_bytes(b"changed")

    with pytest.raises(DocumentStorageError, match="checksum"):
        store.read_bytes(stored.storage_key)
    with pytest.raises(DocumentStorageError, match="invalid"):
        store.read_bytes("../../not-a-document")
