from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.api.schemas import Health
from app.core.config import Settings, get_settings
from app.core.services import Services


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="CaseForge AI", version=__version__)
    app.state.services = services or Services.build(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health", response_model=Health)
    def health() -> Health:
        return Health(
            status="ok",
            version=__version__,
            llm_backend=settings.llm_backend,
            embedding_backend=settings.embedding_backend,
        )

    app.include_router(router)
    return app


app = create_app()
