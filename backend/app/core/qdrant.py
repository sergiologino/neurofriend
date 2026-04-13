from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient | None:
    global _client
    settings = get_settings()
    if not settings.qdrant_url:
        return None
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )
    return _client
