from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.api.errors import GoldAPIError, raise_gold_api_error
from app.core.config import API_LOG_FILE
from app.core.gold_table_validation import validate_gold_base_name
from app.core.logging import setup_logger
from app.repositories.gold_filesystem_repository import expected_table_path
from app.repositories.gold_repository import get_overview, get_table
from app.services.gold_catalog_service import (
    GOLD_CATALOG_JSON,
    filter_catalog,
    load_gold_catalog,
    normalize_catalog_scope_filter,
)
from app.services.gold_service import (
    CompetenciaNotFoundError,
    GoldMonthRef,
    Scope,
    competencia_is_available,
    ensure_competencia_available,
    get_available_tables_for_month,
    get_competencias_payload,
    gold_month_relative_path,
    is_br_only_table,
    relative_project_path,
    resolve_gold_month,
)

router = APIRouter(prefix="/api/gold/v1", tags=["gold"])
logger = setup_logger("api.gold", API_LOG_FILE)


def _parse_scope(scope: str) -> Scope:
    scope = (scope or "").strip().lower()
    if scope in ("br", "pr", "rmc"):
        return scope  # type: ignore[return-value]
    raise_gold_api_error(
        "INVALID_SCOPE",
        "scope inválido. Use: br | pr | rmc",
        {"scope": scope},
        status_code=400,
    )


def _resolve_month(ano: int | None, mes: int | None) -> GoldMonthRef:
    try:
        return resolve_gold_month(ano=ano, mes=mes)
    except ValueError as exc:
        raise GoldAPIError(
            "INVALID_COMPETENCIA",
            str(exc),
            status_code=400,
        ) from exc


def _competencia_error_from_month(month: GoldMonthRef) -> GoldAPIError:
    return GoldAPIError(
        "GOLD_COMPETENCIA_NOT_FOUND",
        "Competência Gold não encontrada.",
        {
            "ano": month.ano,
            "mes": month.mes,
            "expected_path": gold_month_relative_path(month),
        },
        status_code=404,
    )


def _ensure_competencia(month: GoldMonthRef) -> None:
    try:
        ensure_competencia_available(month)
    except CompetenciaNotFoundError as exc:
        logger.warning(
            "Competência Gold não encontrada | ano=%s | mes=%s | path=%s",
            month.ano,
            month.mes,
            gold_month_relative_path(month),
        )
        raise _competencia_error_from_month(exc.month) from exc


def _table_not_found_error(
    month: GoldMonthRef,
    base_name: str,
    scope: Scope,
    path: Path,
) -> GoldAPIError:
    logger.warning(
        "Tabela Gold não encontrada | competencia=%s-%02d | table=%s | scope=%s | path=%s",
        month.ano,
        month.mes,
        base_name,
        scope,
        path,
    )
    return GoldAPIError(
        "GOLD_TABLE_NOT_FOUND",
        "Tabela Gold não encontrada.",
        {
            "ano": month.ano,
            "mes": month.mes,
            "table": base_name,
            "scope": scope,
            "expected_path": relative_project_path(path),
        },
        status_code=404,
    )


def _json_with_obs(result: Any) -> JSONResponse:
    return JSONResponse(
        content=result.payload,
        headers=result.observability_headers(),
    )


@router.get("/catalog")
def catalog(
    ano: int | None = Query(None),
    mes: int | None = Query(None),
    scope: str | None = Query(None),
    granularity: str | None = Query(None),
    suspected_legacy: bool | None = Query(None),
):
    if not GOLD_CATALOG_JSON.is_file():
        logger.warning("Catálogo Gold não encontrado em %s", GOLD_CATALOG_JSON)
        raise_gold_api_error(
            "GOLD_CATALOG_NOT_FOUND",
            "Catálogo Gold não encontrado.",
            {"expected_path": str(GOLD_CATALOG_JSON)},
            status_code=404,
        )

    try:
        payload = load_gold_catalog(GOLD_CATALOG_JSON)
    except OSError as exc:
        logger.error("Falha ao ler catálogo Gold: %s", exc)
        raise GoldAPIError(
            "GOLD_CATALOG_UNREADABLE",
            "Catálogo Gold não pôde ser lido.",
            {"path": str(GOLD_CATALOG_JSON)},
            status_code=500,
        ) from exc

    if scope is not None:
        try:
            normalize_catalog_scope_filter(scope)
        except ValueError as exc:
            raise GoldAPIError(
                "INVALID_SCOPE",
                str(exc),
                {"scope": scope},
                status_code=400,
            ) from exc

    if ano is not None and mes is not None:
        month = _resolve_month(ano, mes)
        _ensure_competencia(month)

    filtered = filter_catalog(
        payload,
        ano=ano,
        mes=mes,
        scope=scope,
        granularity=granularity,
        suspected_legacy=suspected_legacy,
    )
    return filtered


@router.get("/competencias")
def competencias():
    try:
        return get_competencias_payload()
    except OSError as exc:
        logger.error("Falha ao listar competências Gold: %s", exc)
        raise GoldAPIError(
            "INTERNAL_ERROR",
            "Erro ao ler competências disponíveis na camada Gold.",
            status_code=500,
        ) from exc


@router.get("/meta")
def meta(
    ano: int | None = Query(None),
    mes: int | None = Query(None),
):
    month = _resolve_month(ano, mes)
    _ensure_competencia(month)
    return {
        "month": {"ano": month.ano, "mes": month.mes},
        "scopes": [
            {"id": "br", "label": "Brasil"},
            {"id": "pr", "label": "Paraná"},
            {"id": "rmc", "label": "RMC"},
        ],
        "tables": get_available_tables_for_month(month),
    }


@router.get("/table/{base_name}")
def table(
    base_name: str,
    scope: str = Query("br"),
    ano: int | None = Query(None),
    mes: int | None = Query(None),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    sort_by: str | None = None,
    sort_dir: str = Query("desc"),
):
    sc = _parse_scope(scope)
    month = _resolve_month(ano, mes)
    _ensure_competencia(month)

    try:
        safe_base_name = validate_gold_base_name(base_name)
    except ValueError as exc:
        raise GoldAPIError(
            "INVALID_TABLE",
            "Tabela inválida.",
            {"table": base_name},
            status_code=400,
        ) from exc

    if is_br_only_table(safe_base_name) and sc != "br":
        raise GoldAPIError(
            "INVALID_SCOPE",
            f"{safe_base_name} está disponível apenas para scope=br (resumo nacional).",
            {"table": safe_base_name, "scope": sc, "allowed_scopes": ["br"]},
            status_code=400,
        )

    try:
        result = get_table(
            month,
            base_name=safe_base_name,
            scope=sc,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except FileNotFoundError as exc:
        path = expected_table_path(month, base_name=safe_base_name, scope=sc)
        if not competencia_is_available(month):
            raise _competencia_error_from_month(month) from exc
        raise _table_not_found_error(month, safe_base_name, sc, path) from exc
    except ValueError as exc:
        raise GoldAPIError(
            "INVALID_COMPETENCIA",
            str(exc),
            {
                "ano": month.ano,
                "mes": month.mes,
                "table": safe_base_name,
            },
            status_code=400,
        ) from exc

    return _json_with_obs(result)


@router.get("/overview")
def overview(
    scope: str = Query("br"),
    ano: int | None = Query(None),
    mes: int | None = Query(None),
):
    sc = _parse_scope(scope)
    month = _resolve_month(ano, mes)
    _ensure_competencia(month)

    try:
        result = get_overview(month, scope=sc)
    except FileNotFoundError as exc:
        # Extrai nome da tabela da mensagem / path quando possível.
        path = expected_table_path(month, base_name="tabela_municipio", scope=sc)
        raise _table_not_found_error(month, "tabela", sc, path) from exc
    except ValueError as exc:
        msg = str(exc)
        if "Coluna 'uf' ausente" in msg:
            raise_gold_api_error(
                "INTERNAL_ERROR",
                msg,
                status_code=500,
            )
        raise GoldAPIError(
            "INVALID_COMPETENCIA",
            msg,
            {"ano": month.ano, "mes": month.mes},
            status_code=400,
        ) from exc

    return _json_with_obs(result)
