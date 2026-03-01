"""Allow running with `python -m context_bridge`."""

from context_bridge.main import *  # noqa: F401, F403

if __name__ == "__main__":
    import uvicorn
    from context_bridge.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "context_bridge.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        limit_max_requests=settings.limit_max_requests or None,
    )
