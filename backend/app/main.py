from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.routes import ai, assets, attack_paths, graph, health, scans, vulnerabilities
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="AI Network Mapper",
        version="0.1.0",
        description="Defensive network asset, risk, graph, and AI explanation platform.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(scans.router)
    app.include_router(assets.router)
    app.include_router(vulnerabilities.router)
    app.include_router(attack_paths.router)
    app.include_router(graph.router)
    app.include_router(ai.router)
    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()

