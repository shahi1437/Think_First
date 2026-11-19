from fastapi import APIRouter

from app.api.v1.admin_users import admin_users_router
from app.api.v1.health import meta_router
from app.api.v1.users import teacher_identity_router, users_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(meta_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(teacher_identity_router)
api_v1_router.include_router(admin_users_router)
