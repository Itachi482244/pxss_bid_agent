from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


class SPAStaticFiles(StaticFiles):
    """Serve static files with SPA fallback to index.html."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    # Serve frontend static files in production (SPA mode with index.html fallback)
    dist_dir = settings.frontend_dist_dir
    if dist_dir:
        dist_path = Path(dist_dir)
        if dist_path.is_dir():
            app.mount("/", SPAStaticFiles(directory=str(dist_path), html=True), name="frontend")

    return app


app = create_app()
