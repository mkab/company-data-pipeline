from fastapi import APIRouter

from pipeline.api.companies.router import router as companies_router

# Every resource route is mounted here, so its path starts with `/v1`
router = APIRouter(prefix="/v1")
router.include_router(companies_router)
