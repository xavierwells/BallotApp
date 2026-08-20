"""Immutable internal storage for retained source documents.

Stored source artifacts are evidence records, not public downloads.  The
database decides whether a document may be shown publicly; this layer only
stores and verifies bytes by their SHA-256 digest.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


_STORAGE_KEY_PATTERN = re.compile(r"^sha256/([a-f0-9]{2})/([a-f0-9]{64})$")


class DocumentStorageError(RuntimeError):
    """Raised when retained source evidence cannot be safely stored or read."""


@dataclass(frozen=True)
class StoredDocument:
    """Content-addressed location and integrity metadata for a stored artifact."""

    storage_key: str
    checksum_sha256: str
    content_length_bytes: int


class DocumentStore(Protocol):
    """Backend contract for private retained source artifacts."""

    def put_bytes(self, content: bytes) -> StoredDocument: ...

    def read_bytes(self, storage_key: str) -> bytes: ...


class FilesystemDocumentStore:
    """A local, content-addressed store suitable for development and self-hosting."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put_bytes(self, content: bytes) -> StoredDocument:
        checksum = hashlib.sha256(content).hexdigest()
        storage_key = f"sha256/{checksum[:2]}/{checksum}"
        destination = self._path_for_key(storage_key)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        if not destination.exists():
            temporary_file = tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=".upload-",
                delete=False,
            )
            temporary_path = Path(temporary_file.name)
            try:
                with temporary_file:
                    temporary_file.write(content)
                os.chmod(temporary_path, 0o600)
                try:
                    # A hard-link insertion is atomic and never overwrites a
                    # concurrently retained artifact with the same digest.
                    os.link(temporary_path, destination)
                except FileExistsError:
                    pass
                except OSError as error:
                    if not destination.exists():
                        raise DocumentStorageError("could not atomically retain source document") from error
            finally:
                temporary_path.unlink(missing_ok=True)

        retained_content = self.read_bytes(storage_key)
        if retained_content != content:
            raise DocumentStorageError("stored source document checksum does not match uploaded content")
        return StoredDocument(
            storage_key=storage_key,
            checksum_sha256=checksum,
            content_length_bytes=len(content),
        )

    def read_bytes(self, storage_key: str) -> bytes:
        checksum = self._checksum_from_key(storage_key)
        location = self._path_for_key(storage_key)
        try:
            content = location.read_bytes()
        except FileNotFoundError as error:
            raise DocumentStorageError("retained source document is unavailable") from error
        if hashlib.sha256(content).hexdigest() != checksum:
            raise DocumentStorageError("retained source document failed its checksum verification")
        return content

    def _path_for_key(self, storage_key: str) -> Path:
        checksum = self._checksum_from_key(storage_key)
        return self.root / "sha256" / checksum[:2] / checksum

    @staticmethod
    def _checksum_from_key(storage_key: str) -> str:
        match = _STORAGE_KEY_PATTERN.fullmatch(storage_key)
        if match is None or match.group(1) != match.group(2)[:2]:
            raise DocumentStorageError("invalid document storage key")
        return match.group(2)


def document_store_from_environment() -> DocumentStore:
    """Build the configured private store without coupling callers to a vendor."""
    backend = os.getenv("DOCUMENT_STORAGE_BACKEND", "filesystem").strip().lower()
    if backend != "filesystem":
        raise DocumentStorageError(
            "DOCUMENT_STORAGE_BACKEND must be filesystem until an approved S3-compatible adapter is configured"
        )
    root = Path(os.getenv("DOCUMENT_STORAGE_ROOT", "/var/lib/ballot/documents"))
    return FilesystemDocumentStore(root)
