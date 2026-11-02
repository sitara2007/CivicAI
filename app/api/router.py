from fastapi import APIRouter

from app.api.v1.endpoints.health import router as health_router
from app.api.v1.process import router as process_router
from app.api.v1.audit import router as audit_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(process_router)
api_router.include_router(audit_router)
