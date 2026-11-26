"""Add the raw tables.

Revision ID: 54618c306d9f
Revises:
Create Date: 2026-11-26 19:56:17.103526+00:00

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "54618c306d9f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA raw")
    op.execute("GRANT USAGE ON SCHEMA raw TO ingest, dbt")
    # Every table created in raw from now on, these two included, inherits the grants.
    # ingest only appends and dbt only reads, so neither can rewrite the history.
    # Default privileges cover the tables the migrating (owner) role creates, which is every raw table
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT INSERT, SELECT ON TABLES TO ingest")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO dbt")
    op.create_table(
        "edgar_payloads",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("uuid", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sha256", postgresql.BYTEA(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("edgar_payloads_pkey")),
        sa.UniqueConstraint("sha256", name=op.f("edgar_payloads_sha256_key")),
        sa.UniqueConstraint("uuid", name=op.f("edgar_payloads_uuid_key")),
        schema="raw",
    )
    op.create_table(
        "edgar_fetches",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("uuid", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "dataset",
            sa.Enum(
                "company_tickers",
                "submissions",
                "company_facts",
                name="edgar_dataset",
                schema="raw",
            ),
            nullable=False,
        ),
        sa.Column("cik", sa.BigInteger(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("http_status", sa.SmallInteger(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint(
            "(cik IS NULL) = (dataset = 'company_tickers')",
            name=op.f("edgar_fetches_cik_set_per_company_check"),
        ),
        sa.CheckConstraint(
            "(payload_id IS NULL) = (http_status = 404)",
            name=op.f("edgar_fetches_payload_absent_on_not_found_check"),
        ),
        sa.ForeignKeyConstraint(
            ["payload_id"], ["raw.edgar_payloads.id"], name=op.f("edgar_fetches_payload_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("edgar_fetches_pkey")),
        sa.UniqueConstraint("uuid", name=op.f("edgar_fetches_uuid_key")),
        schema="raw",
    )
    op.create_index(
        "edgar_fetches_dataset_cik_fetched_at_index",
        "edgar_fetches",
        ["dataset", "cik", sa.literal_column("fetched_at DESC")],
        unique=False,
        schema="raw",
    )
    op.create_index(
        op.f("edgar_fetches_payload_id_index"),
        "edgar_fetches",
        ["payload_id"],
        unique=False,
        schema="raw",
    )


def downgrade() -> None:
    op.drop_index(op.f("edgar_fetches_payload_id_index"), table_name="edgar_fetches", schema="raw")
    op.drop_index(
        "edgar_fetches_dataset_cik_fetched_at_index", table_name="edgar_fetches", schema="raw"
    )
    op.drop_table("edgar_fetches", schema="raw")
    op.drop_table("edgar_payloads", schema="raw")
    op.execute("DROP TYPE raw.edgar_dataset")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA raw REVOKE SELECT ON TABLES FROM dbt")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA raw REVOKE INSERT, SELECT ON TABLES FROM ingest"
    )
    op.execute("DROP SCHEMA raw")
