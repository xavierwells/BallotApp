"""One authenticated review for official facts; two for interpretive content.

Revision ID: 016_review_policy
Revises: 015_editorial_review
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "016_review_policy"
down_revision = "015_editorial_review"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("verification_events", sa.Column("editorial_user_id", postgresql.UUID(as_uuid=True)))
    op.add_column("verification_events", sa.Column("review_fingerprint", sa.String(64)))
    op.create_foreign_key("fk_verification_staff_publication", "verification_events", "editorial_users",
                          ["editorial_user_id", "publication_id"], ["id", "publication_id"])
    op.execute("""
    CREATE FUNCTION editorial_target_fingerprint(kind text, target uuid) RETURNS text AS $$
    DECLARE snapshot jsonb;
    BEGIN
      IF kind = 'source_claim' THEN
        SELECT jsonb_build_object('id',id,'publication',publication_id,'document',document_id,
          'type',claim_type,'subject_type',subject_type,'subject',subject_id,'text',claim_text,
          'page',source_page,'excerpt',source_excerpt,'confidence',confidence)
        INTO snapshot FROM source_claims WHERE id=target;
      ELSIF kind = 'ballot_version' THEN
        SELECT jsonb_build_object('id',b.id,'publication',b.publication_id,'source',b.official_document_id,
          'election',b.election_id,'identifier',b.external_identifier,
          'items',(SELECT jsonb_agg(to_jsonb(i) ORDER BY i.sequence) FROM ballot_items i WHERE i.ballot_version_id=b.id),
          'geography',(SELECT jsonb_agg(to_jsonb(g) ORDER BY g.geographic_area_id)
            FROM ballot_geographic_requirements g WHERE g.ballot_version_id=b.id),
          'races',(SELECT jsonb_agg(to_jsonb(r) || jsonb_build_object(
              'office',(SELECT to_jsonb(o) FROM offices o WHERE o.id=r.office_id),
              'candidates',(SELECT jsonb_agg(to_jsonb(c) ORDER BY c.id) FROM candidates c WHERE c.race_id=r.id)) ORDER BY r.id)
            FROM races r WHERE r.id IN (SELECT race_id FROM ballot_items WHERE ballot_version_id=b.id)),
          'propositions',(SELECT jsonb_agg(to_jsonb(p) ORDER BY p.id) FROM propositions p
            WHERE p.id IN (SELECT proposition_id FROM ballot_items WHERE ballot_version_id=b.id)))
        INTO snapshot FROM ballot_versions b WHERE b.id=target;
      END IF;
      RETURN encode(sha256(convert_to(snapshot::text,'UTF8')),'hex');
    END;
    $$ LANGUAGE plpgsql STABLE;

    CREATE FUNCTION validate_editorial_verification() RETURNS trigger AS $$
    DECLARE expected text; target_publication uuid;
    BEGIN
      IF NEW.action='verified' AND NEW.target_type IN ('ballot_version','source_claim') THEN
        IF NOT EXISTS(SELECT 1 FROM editorial_users u WHERE u.id=NEW.editorial_user_id
          AND u.publication_id=NEW.publication_id AND u.active AND u.username=NEW.actor_reference)
          OR NEW.actor_role <> 'verifier' THEN
          RAISE EXCEPTION 'verification requires an active authenticated editorial identity';
        END IF;
        IF NEW.target_type='ballot_version' THEN
          SELECT publication_id INTO target_publication FROM ballot_versions WHERE id=NEW.target_id;
        ELSE
          SELECT publication_id INTO target_publication FROM source_claims WHERE id=NEW.target_id;
          IF NEW.source_claim_id IS DISTINCT FROM NEW.target_id THEN
            RAISE EXCEPTION 'source claim verification must reference the same claim';
          END IF;
        END IF;
        IF target_publication IS DISTINCT FROM NEW.publication_id THEN
          RAISE EXCEPTION 'verification target must belong to the staff publication';
        END IF;
        expected := editorial_target_fingerprint(NEW.target_type,NEW.target_id);
        IF expected IS NULL OR NEW.review_fingerprint IS DISTINCT FROM expected THEN
          RAISE EXCEPTION 'verification must match the current content fingerprint';
        END IF;
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    CREATE TRIGGER verification_events_authenticated BEFORE INSERT ON verification_events
      FOR EACH ROW EXECUTE FUNCTION validate_editorial_verification();

    CREATE OR REPLACE FUNCTION require_complete_ballot_before_publication() RETURNS trigger AS $$
    DECLARE reviewers integer;
    BEGIN
      IF NEW.status='published' AND (TG_OP='INSERT' OR OLD.status<>'published') THEN
        IF TG_OP='INSERT' THEN RAISE EXCEPTION 'create a draft ballot before publication'; END IF;
        IF NEW.official_document_id IS DISTINCT FROM OLD.official_document_id
          OR NEW.election_id IS DISTINCT FROM OLD.election_id
          OR NEW.publication_id IS DISTINCT FROM OLD.publication_id
          OR NEW.external_identifier IS DISTINCT FROM OLD.external_identifier THEN
          RAISE EXCEPTION 'review changed ballot content before publication';
        END IF;
        IF NOT EXISTS(SELECT 1 FROM ballot_items WHERE ballot_version_id=NEW.id) THEN
          RAISE EXCEPTION 'a ballot must have items before publication';
        END IF;
        IF EXISTS(SELECT 1 FROM ballot_items WHERE ballot_version_id=NEW.id
          AND NULLIF(BTRIM(source_page),'') IS NULL) THEN
          RAISE EXCEPTION 'every ballot item requires an official-document page citation';
        END IF;
        IF NOT EXISTS(SELECT 1 FROM documents WHERE id=NEW.official_document_id
          AND publication_id=NEW.publication_id AND is_authoritative AND source_type='official_document') THEN
          RAISE EXCEPTION 'ballot publication requires an authoritative official document';
        END IF;
        SELECT COUNT(DISTINCT v.editorial_user_id) INTO reviewers FROM verification_events v
          JOIN editorial_users u ON u.id=v.editorial_user_id AND u.publication_id=v.publication_id AND u.active
          WHERE v.publication_id=NEW.publication_id AND v.target_id=NEW.id AND v.target_type='ballot_version'
          AND v.action='verified' AND v.actor_role='verifier'
          AND v.review_fingerprint=editorial_target_fingerprint('ballot_version',NEW.id);
        IF reviewers<1 THEN RAISE EXCEPTION 'a ballot requires one authenticated review of its current content before publication'; END IF;
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    DROP TRIGGER ballot_versions_require_complete_content ON ballot_versions;
    CREATE TRIGGER ballot_versions_require_complete_content BEFORE INSERT OR UPDATE OF status ON ballot_versions
      FOR EACH ROW EXECUTE FUNCTION require_complete_ballot_before_publication();

    CREATE OR REPLACE FUNCTION require_claim_publication_event() RETURNS trigger AS $$
    DECLARE required integer := 2; reviewers integer;
    BEGIN
      IF NEW.editorial_status='published' THEN
        IF NEW.claim_type='verified_fact' AND EXISTS(SELECT 1 FROM documents WHERE id=NEW.document_id
          AND publication_id=NEW.publication_id AND source_type='official_document' AND is_authoritative) THEN
          required := 1;
        END IF;
        SELECT COUNT(DISTINCT v.editorial_user_id) INTO reviewers FROM verification_events v
          JOIN editorial_users u ON u.id=v.editorial_user_id AND u.publication_id=v.publication_id AND u.active
          WHERE v.publication_id=NEW.publication_id AND v.source_claim_id=NEW.id AND v.target_id=NEW.id
          AND v.target_type='source_claim' AND v.action='verified' AND v.actor_role='verifier'
          AND v.review_fingerprint=editorial_target_fingerprint('source_claim',NEW.id);
        IF reviewers<required THEN
          RAISE EXCEPTION 'published source claim requires % authenticated linked verification event(s) for current content',required;
        END IF;
      END IF;
      RETURN NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    raise NotImplementedError("Provenance migrations are forward-only; restore a verified backup.")
