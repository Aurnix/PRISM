"""PRISM FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prism.config import CORS_ORIGINS


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="PRISM",
        description="Predictive Revenue Intelligence & Signal Mapping",
        version="1.0.0",
    )

    if CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    from prism.api.routes import router
    app.include_router(router)

    return app
