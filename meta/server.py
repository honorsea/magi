"""
MAGI Meta Layer — FastAPI Application Factory.

Creates and configures the FastAPI app with all routers, middleware,
CORS, static file serving, and startup/shutdown lifecycle hooks.
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from magi.meta.services import db as _db
from magi.meta.services import settings_store
from magi.meta.services.sim_manager import get_manager

# Path to built frontend static files
_STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="MAGI Dashboard API",
        description="REST + WebSocket API for the MAGI Framework Dashboard.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Allow all origins in dev. For production, restrict in settings.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Startup / Shutdown ────────────────────────────────────────────────────
    @app.on_event("startup")
    async def _startup():
        await _db.init_db()
        await settings_store.load()
        # Give the simulation manager the current asyncio event loop
        get_manager().set_loop(asyncio.get_event_loop())

    @app.on_event("shutdown")
    async def _shutdown():
        pass  # ThreadPoolExecutor is daemon; threads exit with process

    # ── API Routers ───────────────────────────────────────────────────────────
    from magi.meta.routers import simulation, config, agent, lean, outputs, shortcuts

    app.include_router(simulation.router, prefix="/api/sim",       tags=["Simulation"])
    app.include_router(config.router,     prefix="/api/config",    tags=["Config"])
    app.include_router(agent.router,      prefix="/api/agent",     tags=["Agent"])
    app.include_router(lean.router,       prefix="/api/lean",      tags=["Lean KG"])
    app.include_router(outputs.router,    prefix="/api/outputs",   tags=["Outputs"])
    app.include_router(shortcuts.router,  prefix="/api/shortcuts", tags=["Shortcuts"])

    # ── WebSocket Routers ─────────────────────────────────────────────────────
    from magi.meta.websocket import hub as ws_hub
    app.include_router(ws_hub.router, tags=["WebSocket"])

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["Health"])
    async def health():
        return {"status": "ok", "service": "MAGI Dashboard"}

    # ── Settings endpoint (quick access for frontend branding) ────────────────
    @app.get("/api/branding", tags=["Settings"])
    async def branding():
        return {
            "title":        await settings_store.get("branding.title", "MAGI Dashboard"),
            "subtitle":     await settings_store.get("branding.subtitle", ""),
            "logo_url":     await settings_store.get("branding.logo_url", ""),
            "accent_color": await settings_store.get("branding.accent_color", "hsl(217, 91%, 50%)"),
        }

    # ── Serve frontend SPA (must be LAST — catches all non-API routes) ────────
    _assets_dir = _STATIC_DIR / "assets"
    if _STATIC_DIR.exists() and _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            index = _STATIC_DIR / "index.html"
            if index.exists():
                return FileResponse(str(index))
            return {"detail": "Frontend not built yet. Run: cd frontend && npm run build"}
    else:
        @app.get("/", include_in_schema=False)
        async def serve_dev():
            return {
                "message": "MAGI Dashboard API is running.",
                "docs": "/api/docs",
                "frontend": "Start the Vite dev server: cd frontend && npm run dev",
            }

    return app
