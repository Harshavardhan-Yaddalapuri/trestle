from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import api_router
from backend.api.health import root_router as health_root_router
from backend.core.config import get_settings
from backend.core.errors import register_exception_handlers
from backend.core.logging import configure_logging, get_logger
from backend.db.session import dispose_engine, init_engine
from backend.middleware.request_id import RequestIdMiddleware
from backend.middleware.session import SessionMiddleware
from backend.redis_client import close_redis, init_redis
from backend.services.skills_registry import list_skills


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    init_engine()
    init_redis()
    registered = list_skills(version="v1", status="all")
    logger.info("skills_registered", count=len(registered), ids=[s.id for s in registered])
    logger.info("startup_complete")
    try:
        yield
    finally:
        await close_redis()
        await dispose_engine()
        logger.info("shutdown_complete")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title="Trestle API", lifespan=lifespan)

    # Middleware order: outermost is added last in Starlette, so add CORS last
    # so it wraps everything (and so OPTIONS preflights don't pay session cost).
    app.add_middleware(SessionMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    register_exception_handlers(app)

    app.include_router(health_root_router)
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
