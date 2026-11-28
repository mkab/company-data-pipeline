"""A CIK in a path is 1 to 10 digits, padded or not.

A CIK in a response is 10 digits, zero-padded (`pipeline.cik.PaddedCik`).
"""

from typing import Annotated

from fastapi import Path

# ASCII digits only:
# `\d` would also accept other scripts' digits
CIK_PATTERN = r"^[0-9]{1,10}$"


def cik_from_path(
    cik: Annotated[
        str, Path(pattern=CIK_PATTERN, description="1 to 10 digits, zero-padded or not")
    ],
) -> int:
    """Return the CIK of the `{cik}` path parameter, the dependency every route with one uses."""
    return int(cik)
