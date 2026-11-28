from typing import Annotated

from fastapi import Depends, FastAPI

from pipeline.api.pagination.dependencies import page_request
from pipeline.api.pagination.tests.types import FilingSortKey, PageRequestResponse

# FastAPI reads the route signature at runtime
from pipeline.api.pagination.types import PageRequest  # noqa: TC001
from pipeline.api.problems.exception_handlers import add_exception_handlers


def app_with_a_paginated_list() -> FastAPI:
    """Return an app whose one list route echoes the page request it was given."""
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/filings")
    async def filings(
        page: Annotated[PageRequest[FilingSortKey], Depends(page_request(FilingSortKey))],
    ) -> PageRequestResponse:
        return PageRequestResponse(limit=page.limit, after=page.after)

    return app
