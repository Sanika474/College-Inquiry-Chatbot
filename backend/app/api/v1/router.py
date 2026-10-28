"""API v1 Central Router Aggregation."""

from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.college import router as college_router
from app.api.v1.admin import router as admin_router
from app.api.v1.chat import router as chat_router

api_v1_router = APIRouter()

# Mount endpoints
api_v1_router.include_router(auth_router)
api_v1_router.include_router(college_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(chat_router)

