from typing import Annotated

from fastapi import FastAPI, HTTPException, Query

from pipeline.api.problems.exception_handlers import add_exception_handlers


def app_with_a_query_parameter() -> FastAPI:
    """Return an app whose one route takes `size`, at least 1."""
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/items")
    async def items(size: Annotated[int, Query(ge=1)]) -> dict[str, int]:
        return {"size": size}

    return app


def app_raising_a_404_of_ours() -> FastAPI:
    """Return an app whose one route raises a 404 with a detail of ours."""
    app = FastAPI()
    add_exception_handlers(app)

    @app.get("/concepts/revenues")
    async def concept() -> None:
        raise HTTPException(404, detail="No concept us-gaap/Revenues")

    return app
