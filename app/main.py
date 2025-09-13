"""FastAPI application factory and HTTP middleware.

WHAT: Defines the FastAPI `app` instance, configures logging, CORS, request
timing middleware, mounts API routers (currently climate endpoints) and
exposes a simple `/health` probe.

WHY HERE: This is the top-level web entrypoint used by ASGI servers (e.g.
`uvicorn app.main:app`). It centralizes cross‑cutting concerns (CORS,
logging) before individual feature routers are registered. External
dependencies touched here:
    * FastAPI / Starlette middleware system
    * Application settings via `app.core.config.get_settings`
    * Includes router from `app.api.v1.routes.climate` which ultimately uses
        geocoding (OpenStreetMap Nominatim) and the compact climate model.
"""

import logging
import sys
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1.routes import climate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

settings = get_settings()

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = datetime.now()
        
        # Log incoming request
        logger.info(f"Incoming request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        # Log response
        process_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Request completed: {request.method} {request.url} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        return response

    # include routers
    app.include_router(climate.router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["health"])  # simple health check
    async def health():
        logger.info("Health check requested")
        return {"status": "ok"}

    logger.info(f"Application {settings.app_name} started successfully")
    return app

app = create_app()
