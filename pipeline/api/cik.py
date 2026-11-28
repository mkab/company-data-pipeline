"""A CIK in a path is 1 to 10 digits, padded or not.

A CIK in a response is 10 digits, zero-padded.
"""

from typing import Annotated

from fastapi import Path
from pydantic import PlainSerializer

# ASCII digits only:
# `\d` would also accept other scripts' digits
CIK_PATTERN = r"^[0-9]{1,10}$"
CIK_WIDTH = 10


def cik_from_path(
    cik: Annotated[
        str, Path(pattern=CIK_PATTERN, description="1 to 10 digits, zero-padded or not")
    ],
) -> int:
    """Return the CIK of the `{cik}` path parameter, the dependency every route with one uses."""
    return int(cik)


def padded_cik(cik: int) -> str:
    return str(cik).zfill(CIK_WIDTH)


# A response field holding a CIK:
# an `int` in Python, `"0000320193"` in JSON
PaddedCik = Annotated[int, PlainSerializer(padded_cik, return_type=str)]
