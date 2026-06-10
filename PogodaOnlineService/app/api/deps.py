"""Shared API dependency wiring (placeholder).

WHAT: Currently re-exports climate routes to ensure package import side
effects if needed. Designed to evolve into a place for FastAPI dependency
providers (DB sessions, auth), keeping them decoupled from route modules.

WHY HERE: Centralizing dependency factories aligns with FastAPI best
practices and simplifies future additions without touching each route file.
External APIs: None directly (future: databases, auth providers, etc.).
"""

from .v1.routes import climate  # noqa: F401  (placeholder for shared dependencies later)
