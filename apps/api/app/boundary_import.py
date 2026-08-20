"""Controlled conversion of a retained shapefile ZIP into draft boundaries."""

from __future__ import annotations

import hashlib
import io
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

import shapefile


MAX_BOUNDARY_DOWNLOAD_BYTES = 100 * 1024 * 1024
_SHA256 = re.compile(r"^[a-f0-9]{64}$")


@dataclass(frozen=True)
class BoundaryFeature:
    external_identifier: str
    name: str
    geojson: str
    geometry_checksum_sha256: str


def download_exact_https(url: str, expected_sha256: str) -> bytes:
    """Download a pinned artifact with a size ceiling and checksum requirement."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("boundary source URL must be an absolute HTTPS URL")
    if not _SHA256.fullmatch(expected_sha256):
        raise ValueError("expected SHA-256 must be 64 lowercase hexadecimal characters")

    request = Request(url, headers={"User-Agent": "BallotApp boundary importer/1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - validated HTTPS operator input
        final_url = response.geturl()
        if urlparse(final_url).scheme != "https":
            raise ValueError("boundary download redirected away from HTTPS")
        declared_size = response.headers.get("Content-Length")
        if declared_size and int(declared_size) > MAX_BOUNDARY_DOWNLOAD_BYTES:
            raise ValueError("boundary source exceeds the 100 MiB download limit")
        content = response.read(MAX_BOUNDARY_DOWNLOAD_BYTES + 1)

    if len(content) > MAX_BOUNDARY_DOWNLOAD_BYTES:
        raise ValueError("boundary source exceeds the 100 MiB download limit")
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ValueError(f"boundary source checksum mismatch; received {actual_sha256}")
    return content


def read_shapefile_zip(
    content: bytes,
    *,
    identifier_field: str,
    name_field: str,
    filter_field: str | None = None,
    filter_value: str | None = None,
) -> list[BoundaryFeature]:
    """Read polygon records from one non-nested shapefile in a ZIP archive."""
    try:
        archive = ZipFile(io.BytesIO(content))
    except BadZipFile as error:
        raise ValueError("boundary artifact is not a valid ZIP archive") from error

    component_sets: dict[str, dict[str, str]] = {}
    expanded_size = 0
    for info in archive.infolist():
        path = PurePosixPath(info.filename)
        if info.is_dir() or path.is_absolute() or ".." in path.parts:
            continue
        if info.file_size > MAX_BOUNDARY_DOWNLOAD_BYTES:
            raise ValueError("an archived boundary file exceeds the size limit")
        expanded_size += info.file_size
        if expanded_size > MAX_BOUNDARY_DOWNLOAD_BYTES:
            raise ValueError("expanded boundary archive exceeds the size limit")
        suffix = path.suffix.lower()
        if suffix in {".shp", ".shx", ".dbf"}:
            base = str(path.with_suffix("")).lower()
            component_sets.setdefault(base, {})[suffix] = info.filename
    complete_sets = [members for members in component_sets.values() if set(members) == {".shp", ".shx", ".dbf"}]
    if len(complete_sets) != 1:
        raise ValueError("ZIP must contain exactly one readable .shp/.shx/.dbf dataset")
    members = complete_sets[0]

    reader = shapefile.Reader(
        shp=io.BytesIO(archive.read(members[".shp"])),
        shx=io.BytesIO(archive.read(members[".shx"])),
        dbf=io.BytesIO(archive.read(members[".dbf"])),
    )
    available_fields = {field[0] for field in reader.fields[1:]}
    required_fields = {identifier_field, name_field}
    if filter_field:
        required_fields.add(filter_field)
    missing = required_fields - available_fields
    if missing:
        raise ValueError(f"shapefile is missing required fields: {', '.join(sorted(missing))}")

    features: list[BoundaryFeature] = []
    for shape_record in reader.iterShapeRecords():
        record = shape_record.record.as_dict()
        if filter_field and str(record[filter_field]).strip() != str(filter_value).strip():
            continue
        if shape_record.shape.shapeType not in {
            shapefile.POLYGON,
            shapefile.POLYGONM,
            shapefile.POLYGONZ,
        }:
            raise ValueError("boundary dataset contains a non-polygon shape")
        geometry = shape_record.shape.__geo_interface__
        geojson = json.dumps(geometry, sort_keys=True, separators=(",", ":"))
        features.append(
            BoundaryFeature(
                external_identifier=str(record[identifier_field]).strip(),
                name=str(record[name_field]).strip(),
                geojson=geojson,
                geometry_checksum_sha256=hashlib.sha256(geojson.encode()).hexdigest(),
            )
        )
    if not features:
        raise ValueError("boundary dataset produced no matching polygon records")
    return features
