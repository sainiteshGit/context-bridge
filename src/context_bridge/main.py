"""
Entrypoint — run with `python -m context_bridge` or `uvicorn context_bridge.main:app`.
"""

from context_bridge.api.app import create_app

app = create_app()

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
