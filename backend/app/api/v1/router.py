from fastapi import APIRouter

from app.api.v1.routes import documents, enterprise, projects, system, tasks

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/projects", tags=["documents"])
api_router.include_router(enterprise.router, prefix="/enterprise", tags=["enterprise"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
