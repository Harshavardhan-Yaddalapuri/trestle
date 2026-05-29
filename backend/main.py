import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.api import api_router
from backend.api.health import root_router as health_root_router
from backend.core.config import get_settings
from backend.core.errors import register_exception_handlers
from backend.core.logging import configure_logging, get_logger
from backend.db.session import dispose_engine, get_engine, init_engine
from backend.middleware.request_id import RequestIdMiddleware
from backend.middleware.session import SessionMiddleware
from backend.redis_client import close_redis, init_redis
from backend.services.scheduler import url_verify_scheduler
from backend.services.skills_registry import list_skills

_GRANTS_SEED_DIR = Path(__file__).parent / "seed" / "grants"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = get_logger(__name__)
    init_engine()
    init_redis()
    registered = list_skills(version="v1", status="all")
    logger.info("skills_registered", count=len(registered), ids=[s.id for s in registered])

    settings = get_settings()
    if settings.is_dev and _GRANTS_SEED_DIR.is_dir():
        try:
            from backend.seed.loader import load_grants_from_dir, upsert_grants

            grants = load_grants_from_dir(_GRANTS_SEED_DIR)
            factory = async_sessionmaker(
                get_engine(), expire_on_commit=False, class_=AsyncSession
            )
            async with factory() as session:
                inserted, updated = await upsert_grants(session, grants)
            logger.info("grants_seed_complete", inserted=inserted, updated=updated)
        except Exception:
            logger.exception("grants_seed_failed")

    scheduler_task: asyncio.Task | None = None
    if settings.URL_VERIFY_ENABLED:
        scheduler_task = asyncio.create_task(url_verify_scheduler())

    logger.info("startup_complete")
    try:
        yield
    finally:
        if scheduler_task is not None:
            scheduler_task.cancel()
            try:
                await scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("url_verify_scheduler_stopped")
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
