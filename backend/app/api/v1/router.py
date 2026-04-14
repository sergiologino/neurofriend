from fastapi import APIRouter

from app.api.v1.routes import conversations, debug, health, initiative, internal_initiative, meta, neurofriends, perception

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(meta.router, prefix="/meta", tags=["meta"])
api_router.include_router(neurofriends.router, prefix="/neurofriends", tags=["neurofriends"])
api_router.include_router(initiative.router, prefix="/neurofriends", tags=["initiative"])
api_router.include_router(perception.router, prefix="/perception", tags=["perception"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(debug.router, tags=["debug"])
api_router.include_router(internal_initiative.router, prefix="/internal", tags=["internal"])
