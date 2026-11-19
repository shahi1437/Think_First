from fastapi import APIRouter

from app.api.v1.admin_problems import admin_languages_router, admin_problems_router
from app.api.v1.admin_users import admin_users_router
from app.api.v1.health import meta_router
from app.api.v1.problems import languages_router, problems_router
from app.api.v1.submissions import submissions_router, workspace_router
from app.api.v1.users import teacher_identity_router, users_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(meta_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(teacher_identity_router)
api_v1_router.include_router(admin_users_router)
api_v1_router.include_router(languages_router)
api_v1_router.include_router(problems_router)
api_v1_router.include_router(submissions_router)
api_v1_router.include_router(workspace_router)
api_v1_router.include_router(admin_problems_router)
api_v1_router.include_router(admin_languages_router)
