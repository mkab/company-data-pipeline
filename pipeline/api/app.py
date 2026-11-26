from fastapi import FastAPI

from pipeline.api.health import router as health_router


def create_app() -> FastAPI:
    """Build the API application."""
    app = FastAPI(title="Company data pipeline")
    app.include_router(health_router)
    return app
