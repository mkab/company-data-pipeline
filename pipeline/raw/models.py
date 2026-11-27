from datetime import datetime
from enum import StrEnum
from http import HTTPStatus

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pipeline.database import RAW_SCHEMA, ModelBase


class EdgarDataset(StrEnum):
    COMPANY_TICKERS = "company_tickers"
    SUBMISSIONS = "submissions"
    COMPANY_FACTS = "company_facts"


# Tables are declarative models inheriting from `ModelBase` (a `sqlalchemy.orm.DeclarativeBase`),
# not Core `sa.Table`s: the columns are typed, and the standard columns come from `ModelBase`


class EdgarPayload(ModelBase):
    """One distinct body: fetches that return the same bytes share it."""

    __tablename__ = "edgar_payloads"
    __table_args__ = {"schema": RAW_SCHEMA}

    sha256: Mapped[bytes] = mapped_column(BYTEA, unique=True)
    payload: Mapped[object] = mapped_column(JSONB)


class EdgarFetch(ModelBase):
    """One fetch, appended on every run and never updated."""

    __tablename__ = "edgar_fetches"
    __table_args__ = (
        # The tickers file covers every company, the other datasets one company each
        sa.CheckConstraint(
            sa.column("cik").is_(None)
            == (sa.column("dataset") == EdgarDataset.COMPANY_TICKERS.value),
            name="cik_set_per_company",
        ),
        # A 404 is the one recorded fetch with no body worth keeping ("no facts")
        sa.CheckConstraint(
            sa.column("payload_id").is_(None)
            == (sa.column("http_status") == HTTPStatus.NOT_FOUND.value),
            name="payload_absent_on_not_found",
        ),
        sa.Index(
            "edgar_fetches_dataset_cik_fetched_at_index",
            "dataset",
            "cik",
            sa.text("fetched_at DESC"),
        ),
        {"schema": RAW_SCHEMA},
    )

    dataset: Mapped[EdgarDataset] = mapped_column(
        sa.Enum(
            EdgarDataset,
            name="edgar_dataset",
            schema=RAW_SCHEMA,
            # The values, not the member names, are stored
            values_callable=lambda dataset: [member.value for member in dataset],
        )
    )
    cik: Mapped[int | None] = mapped_column(sa.BigInteger)
    url: Mapped[str] = mapped_column(sa.Text)
    http_status: Mapped[int] = mapped_column(sa.SmallInteger)
    fetched_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True))
    payload_id: Mapped[int | None] = mapped_column(
        sa.BigInteger, sa.ForeignKey(EdgarPayload.id), index=True
    )
