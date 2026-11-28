from fastapi import FastAPI

from pipeline.api.health import router as health_router
from pipeline.api.problems.exception_handlers import add_exception_handlers
from pipeline.api.v1 import router as v1_router


def create_app() -> FastAPI:
    """Build the API application, its OpenAPI docs served at `/docs`."""
    app = FastAPI(title="Company data pipeline")
    add_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router)
    return app
