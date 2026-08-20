"""Separate a boundary publisher from the authority the boundary describes.

Revision ID: 010_boundary_source_roles
Revises: 009_boundary_foundations
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "010_boundary_source_roles"
down_revision = "009_boundary_foundations"
branch_labels = None
depends_on = None

uuid = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # A publisher (for example, the Texas Legislative Council) may publish a
    # boundary whose responsible authority is a county. Preserve both facts.
    op.drop_constraint("fk_boundary_versions_dataset_authority", "boundary_versions", type_="foreignkey")
    op.drop_index("ix_boundary_datasets_authority_status", table_name="boundary_datasets")
    op.drop_constraint("uq_boundary_datasets_id_authority", "boundary_datasets", type_="unique")
    op.drop_constraint("fk_boundary_datasets_registry_authority", "boundary_datasets", type_="foreignkey")

    op.alter_column(
        "boundary_datasets",
        "authority_id",
        new_column_name="publisher_authority_id",
        existing_type=uuid,
        existing_nullable=False,
    )
    op.add_column("boundary_datasets", sa.Column("subject_authority_id", uuid, nullable=True))
    op.add_column(
        "boundary_datasets",
        sa.Column(
            "source_document_id",
            uuid,
            sa.ForeignKey("documents.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE boundary_datasets SET subject_authority_id = publisher_authority_id "
        "WHERE subject_authority_id IS NULL"
    )
    op.alter_column(
        "boundary_datasets", "subject_authority_id", existing_type=uuid, nullable=False
    )

    op.create_foreign_key(
        "fk_boundary_datasets_registry_publisher",
        "boundary_datasets",
        "authority_source_registry",
        ["authority_source_registry_id", "publisher_authority_id"],
        ["id", "authority_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_boundary_datasets_subject_authority",
        "boundary_datasets",
        "election_authorities",
        ["subject_authority_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_boundary_datasets_id_subject_authority",
        "boundary_datasets",
        ["id", "subject_authority_id"],
    )
    op.create_index(
        "ix_boundary_datasets_subject_status",
        "boundary_datasets",
        ["subject_authority_id", "status", "checked_at"],
    )
    op.create_index(
        "ix_boundary_datasets_publisher",
        "boundary_datasets",
        ["publisher_authority_id", "checked_at"],
    )
    op.create_foreign_key(
        "fk_boundary_versions_dataset_subject_authority",
        "boundary_versions",
        "boundary_datasets",
        ["boundary_dataset_id", "authority_id"],
        ["id", "subject_authority_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Provenance migrations are forward-only. Restore a verified backup for a destructive rollback."
    )
