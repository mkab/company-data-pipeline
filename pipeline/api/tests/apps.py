from typing import Annotated

from fastapi import Depends, FastAPI

from pipeline.api.cik import cik_from_path
from pipeline.api.problems.exception_handlers import add_exception_handlers
from pipeline.api.tests.types import CompanyResponse


def app_with_a_cik_path() -> FastAPI:
    """Return an app whose one route reads a `{cik}` path parameter and returns it padded."""
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/companies/{cik}")
    async def company(cik: Annotated[int, Depends(cik_from_path)]) -> CompanyResponse:
        return CompanyResponse(cik=cik)

    return app
