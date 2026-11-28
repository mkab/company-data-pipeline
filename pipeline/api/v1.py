from fastapi import APIRouter

# Every resource route is mounted here, so its path starts with `/v1`
router = APIRouter(prefix="/v1")
