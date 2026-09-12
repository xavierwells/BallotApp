"""One-time local staff setup and unreviewed intake of the downloaded pilot data."""

import argparse
from datetime import UTC, datetime
from getpass import getpass
import hashlib
from pathlib import Path

from sqlalchemy import text

from app.cli.bootstrap_authorities import bootstrap, default_manifest_path, read_manifest as read_authorities
from app.cli.intake_document import intake_document, parse_timestamp
from app.cli.review_source import review_source
from app.cli.stage_candidate_certification import read_manifest
from app.database import get_engine
from app.editorial_auth import create_user, hash_password
from app.editorial_review import stage_batch


def prepare(data_root: Path, username: str, password: str | None) -> list[str]:
    manifests = [read_manifest(data_root / "candidates" / f"texas-2026-general-{county}-certification.json")
                 for county in ("bell", "coryell", "lampasas")]
    source = manifests[0]["sourceDocument"]
    pdf = data_root / "private" / "2026-ballot-cert.pdf"
    if not pdf.is_file():
        raise ValueError("Download the certification with source-fetch first; data/private/2026-ballot-cert.pdf is missing.")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if any(m["sourceDocument"]["checksumSha256"] != digest or m["sourceDocument"]["sourceUrl"] != source["sourceUrl"]
           for m in manifests):
        raise ValueError("The retained PDF does not match all three staging manifests.")
    if password is not None:
        hash_password(password)  # Validate before beginning setup.
    bootstrap(read_authorities(data_root / "authorities" / "copperas-cove-pilot.json"))
    engine = get_engine()
    with engine.connect() as connection:
        publication_id = connection.execute(text(
            "SELECT p.id FROM publications p JOIN organizations o ON o.id=p.organization_id "
            "WHERE p.slug=:p AND o.slug=:o"
        ), {"p": manifests[0]["publicationSlug"], "o": manifests[0]["organizationSlug"]}).scalar_one()
        disposition = connection.execute(text(
            "SELECT s.approval_status,s.permitted_use FROM authority_source_registry s "
            "JOIN election_authorities a ON a.id=s.authority_id "
            "WHERE a.publication_id=:p AND a.slug='texas-secretary-of-state-elections' AND s.slug='2026-ballot-certification'"
        ), {"p": publication_id}).mappings().one()
    if disposition["approval_status"] in {"rejected", "retired"}:
        raise ValueError("This source has been rejected or retired. Resolve that source disposition before setup.")
    if disposition["approval_status"] == "pending_review":
        review_source(engine=engine, organization_slug=manifests[0]["organizationSlug"],
                      publication_slug=manifests[0]["publicationSlug"], authority_slug="texas-secretary-of-state-elections",
                      source_slug="2026-ballot-certification", approval_status="approved", permitted_use="private_retention",
                      reviewer_reference=f"setup:{username}", reviewed_at=datetime.now(UTC),
                      review_notes="Owner-approved pilot policy: private retention and official factual extraction. Content awaits human review.",
                      terms_url="https://www.sos.state.tx.us/elections/laws/2026-november-general-election.shtml",
                      source_license="Reuse terms not explicit; owner-approved official-fact policy, no public source copy",
                      cost_model="free public download", rate_limit="manual pinned download only",
                      retention_rule="retain privately for provenance", attribution_requirement="Texas Secretary of State, Elections Division",
                      redistribution_rights="metadata_only", next_review_at=None, automated_monitoring_allowed=False)
    elif disposition["permitted_use"] not in {"private_retention", "public_copy"}:
        raise ValueError("Existing source approval does not permit retention; review that disposition before setup.")
    document_id = intake_document(
        organization_slug=manifests[0]["organizationSlug"], publication_slug=manifests[0]["publicationSlug"],
        authority_slug="texas-secretary-of-state-elections", source_slug="2026-ballot-certification", file_path=pdf,
        title=source["title"], publisher_name=source["publisherName"], source_url=source["sourceUrl"],
        retrieved_at=parse_timestamp(source["retrievedAt"]), document_published_at=parse_timestamp(source["publishedAt"]),
        public_access_level="metadata_only")
    with engine.begin() as connection:
        existing = connection.execute(text("SELECT publication_id FROM editorial_users WHERE username=:u"),
                                      {"u": username}).scalar_one_or_none()
        if existing is not None and existing != publication_id:
            raise ValueError("This username already belongs to another publication.")
        if existing is None:
            if password is None:
                raise ValueError("A new staff account requires a password.")
            create_user(connection, publication_id, username, password)
        return [stage_batch(connection, publication_id, document_id, m) for m in manifests]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the three county review tasks; no facts are verified or published")
    parser.add_argument("--username", required=True)
    parser.add_argument("--data-root", type=Path, default=default_manifest_path().parent.parent)
    args = parser.parse_args()
    with get_engine().connect() as connection:
        exists = connection.execute(text("SELECT id FROM editorial_users WHERE username=:u"), {"u": args.username}).scalar_one_or_none()
    password = None
    if exists is None:
        password = getpass("New editorial passphrase (15+ characters): ")
        if password != getpass("Repeat passphrase: "):
            raise SystemExit("Passphrases did not match. No changes made.")
    try:
        batches = prepare(args.data_root, args.username, password)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"Ready: {len(batches)} private county review tasks. Existing reviews are preserved on an unchanged rerun.")
    print("Open the web application's /editorial page and sign in. No facts were marked verified or published.")


if __name__ == "__main__":
    main()
