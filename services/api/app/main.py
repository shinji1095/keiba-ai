from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, health, races, scrape, venues
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db.session import init_db


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="Keiba AI API",
    )

    # CORS: keep permissive in local; tighten in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    app.include_router(venues.router, tags=["venues"])
    app.include_router(races.router, tags=["races"])
    app.include_router(scrape.router, tags=["scrape"])

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    return app


app = create_app()
