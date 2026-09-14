"""API v1 root router aggregating feature endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import chat, health

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(chat.router)
