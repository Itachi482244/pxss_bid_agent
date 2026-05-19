from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/info")
async def system_info() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
    }

