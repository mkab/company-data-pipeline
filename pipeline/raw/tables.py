from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import BYTEA, JSONB

from pipeline.database import alembic_metadata


class EdgarDataset(StrEnum):
    COMPANY_TICKERS = "company_tickers"
    SUBMISSIONS = "submissions"
    COMPANY_FACTS = "company_facts"


RAW_SCHEMA = "raw"


def standard_columns() -> list[sa.Column[object]]:
    """Return the columns every table starts with (see `CODING_STANDARDS.md`)."""
    return [
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "uuid",
            sa.Uuid,
            server_default=sa.text("gen_random_uuid()"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


# One row per distinct body: fetches that return the same bytes share it
edgar_payloads = sa.Table(
    "edgar_payloads",
    alembic_metadata,
    *standard_columns(),
    sa.Column("sha256", BYTEA, unique=True, nullable=False),
    sa.Column("payload", JSONB, nullable=False),
    schema=RAW_SCHEMA,
)

# One row per fetch, appended on every run and never updated
edgar_fetches = sa.Table(
    "edgar_fetches",
    alembic_metadata,
    *standard_columns(),
    sa.Column(
        "dataset",
        sa.Enum(
            EdgarDataset,
            name="edgar_dataset",
            schema=RAW_SCHEMA,
            # The values, not the member names, are stored
            values_callable=lambda dataset: [member.value for member in dataset],
        ),
        nullable=False,
    ),
    sa.Column("cik", sa.BigInteger),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("http_status", sa.SmallInteger, nullable=False),
    sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("payload_id", sa.BigInteger, sa.ForeignKey(edgar_payloads.c.id)),
    # The tickers file covers every company, the other datasets one company each
    sa.CheckConstraint(
        "(cik IS NULL) = (dataset = 'company_tickers')", name="cik_set_per_company"
    ),
    # A 404 is the one recorded fetch with no body worth keeping ("no facts")
    sa.CheckConstraint(
        "(payload_id IS NULL) = (http_status = 404)", name="payload_absent_on_not_found"
    ),
    sa.Index(
        "edgar_fetches_dataset_cik_fetched_at_index",
        "dataset",
        "cik",
        sa.text("fetched_at DESC"),
    ),
    sa.Index(None, "payload_id"),
    schema=RAW_SCHEMA,
)
