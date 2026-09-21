from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import GoldAPIError
from app.api.routes_admin import router as admin_router
from app.api.routes_debug import router as debug_router
from app.api.routes_gold import router as gold_router
from app.api.routes_ict import router as ict_router
from app.api.routes_ictt_v2 import router as ictt_v2_router
from app.api.routes_map import router as map_router
from app.api.routes_ops import router as ops_router
from app.core.config import (
    API_LOG_FILE,
    CORS_ALLOWED_ORIGINS,
    ENABLE_ADMIN_ROUTES,
    ENABLE_DEBUG_ROUTES,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_MINUTE,
    is_production_env,
    resolve_gold_backend,
)
from app.core.logging import setup_logger
from app.core.production_config import assert_production_config
from app.core.public_errors import sanitize_public_error_details
from app.core.rate_limit import RateLimitMiddleware
from app.core.security_headers import SecurityHeadersMiddleware
from app.services.gold_readiness import build_readiness_report

logger = setup_logger("api", API_LOG_FILE)


def create_app() -> FastAPI:
    assert_production_config()

    docs_kwargs: dict[str, str | None] = {}
    if is_production_env():
        docs_kwargs = {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }

    application = FastAPI(
        title="Projeto CAGED API",
        version="1.0.0",
        openapi_tags=[
            {
                "name": "ict-v2",
                "description": (
                    "ICTT methodology version 2.0. Endpoints versionados em paralelo "
                    "à V1 (/api/ict/v1), que permanece ativa e não depreciada. "
                    "Fonte canônica: Gold Parquet ictt_v2. A API não recalcula o índice."
                ),
            }
        ],
        **docs_kwargs,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=[
            "X-Gold-Backend",
            "X-Data-Source",
            "X-Fallback-Used",
        ],
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        RateLimitMiddleware,
        enabled=RATE_LIMIT_ENABLED,
        per_minute=RATE_LIMIT_PER_MINUTE,
    )

    application.include_router(map_router)
    application.include_router(gold_router)
    application.include_router(ict_router)
    application.include_router(ictt_v2_router)
    application.include_router(ops_router)

    if ENABLE_ADMIN_ROUTES:
        application.include_router(admin_router)

    if ENABLE_DEBUG_ROUTES:
        application.include_router(debug_router)

    @application.exception_handler(GoldAPIError)
    async def gold_api_error_handler(_request: Request, exc: GoldAPIError) -> JSONResponse:
        logger.warning(
            "Gold API error | code=%s | message=%s | details=%s",
            exc.code,
            exc.message,
            exc.details,
        )
        payload = exc.to_payload()
        payload["error"]["details"] = sanitize_public_error_details(payload["error"].get("details"))
        return JSONResponse(status_code=exc.status_code, content=payload)

    @application.on_event("startup")
    def on_startup() -> None:
        logger.info(
            "API iniciada | service=caged-dashboard-api | env=%s | version=%s | "
            "debug_routes=%s | admin_routes=%s | rate_limit=%s | gold_backend=%s",
            os.getenv("APP_ENV", "local"),
            os.getenv("APP_VERSION", "dev"),
            ENABLE_DEBUG_ROUTES,
            ENABLE_ADMIN_ROUTES,
            RATE_LIMIT_ENABLED,
            resolve_gold_backend(),
        )

    @application.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "caged-dashboard-api",
            "version": os.getenv("APP_VERSION", "dev"),
            "environment": os.getenv("APP_ENV", "local"),
        }

    @application.get("/ready")
    def ready():
        report = build_readiness_report()
        status_code = 200 if report["status"] == "ready" else 503
        return JSONResponse(status_code=status_code, content=report)

    return application


app = create_app()
