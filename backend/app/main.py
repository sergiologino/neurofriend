from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.services.semantic_memory import init_semantic_collection, shutdown_semantic_memory


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_semantic_collection()
    yield
    await shutdown_semantic_memory()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="NeuroFriend API", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def root_health() -> dict[str, str]:
        return {"status": "ok"}
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/v1")
    return app


app = create_app()
