"""A CIK as the pipeline shows it: 10 digits, zero-padded, such as `"0000320193"`."""

from typing import Annotated

from pydantic import PlainSerializer

CIK_WIDTH = 10


def padded_cik(cik: int) -> str:
    return str(cik).zfill(CIK_WIDTH)


# A response field holding a CIK:
# an `int` in Python, `"0000320193"` in JSON
PaddedCik = Annotated[int, PlainSerializer(padded_cik, return_type=str)]
