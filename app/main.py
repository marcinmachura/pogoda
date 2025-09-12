from fastapi import FastAPI
from app.core.config import get_settings
from app.api.v1.routes import climate

settings = get_settings()

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    # include routers
    app.include_router(climate.router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["health"])  # simple health check
    async def health():
        return {"status": "ok"}

    return app

app = create_app()
