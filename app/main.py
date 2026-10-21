from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.auth import router as auth_router
from .config import get_settings
from .db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Elf Studio 后端：当前提供登录认证，后续接入任务与资产生成。",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["系统"], summary="健康检查")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
