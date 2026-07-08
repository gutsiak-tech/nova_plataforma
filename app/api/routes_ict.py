from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.config import API_LOG_FILE
from app.core.logging import setup_logger
from app.repositories.ict_report_repository import get_report_context
from app.services.ict_report_context_service import REPORT_SCOPE_UNSUPPORTED_MSG

router = APIRouter(prefix="/api/ict/v1", tags=["ict"])
logger = setup_logger("api.ict", API_LOG_FILE)


@router.get(
    "/report-context",
    summary="Contexto analítico determinístico do ICT",
    description=(
        "Lê ou gera o contexto analítico do ICT a partir da camada Gold "
        "(filesystem ou PostGIS conforme GOLD_BACKEND). "
        "Não utiliza IA nem serviços externos."
    ),
)
def report_context(
    scope: str = Query("pr", description="Escopo territorial (apenas pr nesta fase)"),
    ano: int = Query(..., ge=2000, le=2100),
    mes: int = Query(..., ge=1, le=12),
):
    scope_key = (scope or "").strip().lower()
    if scope_key != "pr":
        raise HTTPException(status_code=400, detail=REPORT_SCOPE_UNSUPPORTED_MSG)

    try:
        result = get_report_context(scope_key, ano, mes)
        logger.info(
            "ICT report context | scope=%s | ano=%s | mes=%02d | cache=%s | "
            "backend=%s | data_source=%s | fallback=%s",
            scope_key,
            ano,
            mes,
            result.payload.get("cache_status"),
            result.gold_backend,
            result.data_source,
            result.fallback_used,
        )
        return JSONResponse(
            content=result.payload,
            headers=result.observability_headers(),
        )
    except FileNotFoundError as exc:
        logger.warning("ICT report context not found | %s", exc)
        raise HTTPException(
            status_code=404,
            detail=(
                "Não foi possível gerar o relatório determinístico do ICT: "
                "dados Gold do ICT indisponíveis para esta competência."
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
