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
from app.api.routes_map import router as map_router
from app.api.routes_ops import router as ops_router
from app.core.config import API_LOG_FILE, CORS_ALLOWED_ORIGINS, ENABLE_DEBUG_ROUTES, resolve_gold_backend
from app.core.logging import setup_logger
from app.core.public_errors import sanitize_public_error_details
from app.services.gold_readiness import build_readiness_report

logger = setup_logger("api", API_LOG_FILE)

app = FastAPI(title="Projeto CAGED API", version="1.0.0")

app.add_middleware(
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

app.include_router(map_router)
app.include_router(gold_router)
app.include_router(ict_router)
app.include_router(ops_router)
app.include_router(admin_router)

if ENABLE_DEBUG_ROUTES:
    app.include_router(debug_router)


@app.exception_handler(GoldAPIError)
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


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "API iniciada | service=caged-dashboard-api | env=%s | version=%s | debug_routes=%s | gold_backend=%s",
        os.getenv("APP_ENV", "local"),
        os.getenv("APP_VERSION", "dev"),
        ENABLE_DEBUG_ROUTES,
        resolve_gold_backend(),
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "caged-dashboard-api",
        "version": os.getenv("APP_VERSION", "dev"),
        "environment": os.getenv("APP_ENV", "local"),
    }


@app.get("/ready")
def ready():
    report = build_readiness_report()
    status_code = 200 if report["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=report)
