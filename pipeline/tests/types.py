from pydantic import BaseModel

from pipeline.cik import PaddedCik


class CikResponse(BaseModel):
    """A response with one CIK field, to see how `PaddedCik` serialises."""

    cik: PaddedCik
