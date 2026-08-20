import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest
import shapefile

from app.boundary_import import download_exact_https, read_shapefile_zip


def make_boundary_zip(tmp_path: Path) -> bytes:
    base = tmp_path / "precincts"
    with shapefile.Writer(str(base), shapeType=shapefile.POLYGON) as writer:
        writer.field("PRECINCT", "C")
        writer.field("LABEL", "C")
        writer.field("COUNTY", "C")
        writer.poly([[[-97.91, 31.10], [-97.89, 31.10], [-97.89, 31.12], [-97.91, 31.12], [-97.91, 31.10]]])
        writer.record("101", "Precinct 101", "Bell")
        writer.poly([[[-97.81, 31.20], [-97.79, 31.20], [-97.79, 31.22], [-97.81, 31.22], [-97.81, 31.20]]])
        writer.record("201", "Precinct 201", "Coryell")

    archive_path = tmp_path / "precincts.zip"
    with ZipFile(archive_path, "w") as archive:
        for suffix in ("shp", "shx", "dbf"):
            archive.write(base.with_suffix(f".{suffix}"), f"data/precincts.{suffix}")
    return archive_path.read_bytes()


def test_reads_and_filters_polygon_shapefile(tmp_path: Path) -> None:
    features = read_shapefile_zip(
        make_boundary_zip(tmp_path),
        identifier_field="PRECINCT",
        name_field="LABEL",
        filter_field="COUNTY",
        filter_value="Bell",
    )

    assert len(features) == 1
    assert features[0].external_identifier == "101"
    assert features[0].name == "Precinct 101"
    assert len(features[0].geometry_checksum_sha256) == 64


def test_rejects_missing_required_field(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="MISSING"):
        read_shapefile_zip(
            make_boundary_zip(tmp_path),
            identifier_field="MISSING",
            name_field="LABEL",
        )


def test_download_requires_https_and_pinned_checksum() -> None:
    digest = hashlib.sha256(b"test").hexdigest()
    with pytest.raises(ValueError, match="HTTPS"):
        download_exact_https("http://example.test/boundaries.zip", digest)
    with pytest.raises(ValueError, match="SHA-256"):
        download_exact_https("https://example.test/boundaries.zip", "untrusted")
