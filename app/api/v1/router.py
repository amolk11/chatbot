"""API v1 root router aggregating feature endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_v1_router = APIRouter()

# Register endpoint routers
# Note: Health probes are exposed both at root (/health) and under /api/v1/health for convenience
api_v1_router.include_router(health.router)
