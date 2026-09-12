"""Fetch one explicitly named public source into private local evidence storage."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import urllib.request


def fetch(url: str, destination: Path, expected_sha256: str) -> tuple[str, int]:
    if not url.startswith("https://"):
        raise ValueError("source URL must use HTTPS")
    expected_sha256 = expected_sha256.lower()
    if len(expected_sha256) != 64 or any(character not in "0123456789abcdef" for character in expected_sha256):
        raise ValueError("expected SHA-256 must contain 64 hexadecimal characters")

    request = urllib.request.Request(url, headers={"User-Agent": "BallotApp/0.1 manual-source-intake"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content = response.read()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"download checksum mismatch: expected {expected_sha256}, got {actual_sha256}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(content)
    temporary.replace(destination)
    return actual_sha256, len(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually fetch and checksum one public source document")
    parser.add_argument("--url", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    arguments = parser.parse_args()
    checksum, length = fetch(arguments.url, arguments.destination, arguments.expected_sha256)
    print(f"Private source retrieved: {arguments.destination} ({length} bytes, sha256 {checksum})")


if __name__ == "__main__":
    main()
