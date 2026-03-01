"""
FastAPI Application Factory.

Creates and configures the app with:
  - CORS middleware (for browser extension)
  - Dependency injection (storage backend from config)
  - All route modules mounted
  - Health endpoint
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from context_bridge.api.dependencies import get_token_service, init_container
from context_bridge.api.routes import bridge, consent, facts, users
from context_bridge.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    settings: Settings = get_settings()
    init_container(settings)
    app.state.token_service = get_token_service()
    yield  # app runs
    # shutdown logic (if needed) goes here


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Build and return the FastAPI instance.

    Usage:
        app = create_app()        # uses env/defaults
        app = create_app(custom)   # testing overrides
    """
    s = settings or get_settings()

    app = FastAPI(
        title=s.app_name,
        description=(
            "Context Bridge — a personal, user-owned context layer "
            "that lets your preferences and memories flow across AI apps."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── CORS (browser extension + local dev) ──────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(facts.router, prefix="/api/v1")
    app.include_router(consent.router, prefix="/api/v1")
    app.include_router(bridge.router, prefix="/api/v1")

    # ── Health ────────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "context-bridge"}

    return app
