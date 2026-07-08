"""Orquestrador do ICT report-context: filesystem | PostGIS com fallback."""

from __future__ import annotations

from typing import Any

from app.core.config import API_LOG_FILE, GOLD_BACKEND, resolve_gold_backend
from app.core.fallback_registry import record_fallback
from app.core.logging import setup_logger
from app.repositories.gold_postgis_repository import (
    PostgisUnavailableError,
    fetch_ictt_pr_dataframe,
    list_ictt_pr_competencias_upto,
)
from app.repositories.gold_repository import GoldFetchResult
from app.services.ict_report_context_service import get_or_build_ict_report_payload
from pipelines.gold.compute_ict_report_context import (
    _monthly_snapshot,
    build_report_context,
    render_report_context_markdown,
    validate_report_context,
)

logger = setup_logger("api.ict.repository", API_LOG_FILE)

ENDPOINT = "/api/ict/v1/report-context"
MIN_EXPECTED_ROWS = 1


def _configured_backend() -> str:
    try:
        return resolve_gold_backend()
    except Exception:  # noqa: BLE001
        return GOLD_BACKEND if GOLD_BACKEND in {"filesystem", "postgis"} else "filesystem"


def _filesystem_payload(scope: str, ano: int, mes: int) -> dict[str, Any]:
    return get_or_build_ict_report_payload(scope, ano, mes)


def _log_and_record_fallback(
    *,
    scope: str,
    ano: int,
    mes: int,
    reason: str,
) -> None:
    logger.warning(
        "[DATA_SOURCE] fallback usado | endpoint=%s | table_name=%s | scope=%s | "
        "ano=%s | mes=%s | motivo=%s",
        ENDPOINT,
        "tabela_ictt_municipio",
        scope,
        ano,
        mes,
        reason,
    )
    record_fallback(
        endpoint=ENDPOINT,
        table_name="tabela_ictt_municipio",
        scope=scope,
        ano=ano,
        mes=mes,
        reason=reason,
    )


def _build_postgis_payload(scope: str, ano: int, mes: int) -> dict[str, Any]:
    if scope != "pr":
        raise PostgisUnavailableError(f"scope_nao_suportado_postgis: {scope}")

    df = fetch_ictt_pr_dataframe(ano=ano, mes=mes)
    if len(df) < MIN_EXPECTED_ROWS:
        raise PostgisUnavailableError(
            f"sem_dados: fact_ictt_municipio_pr_mes ano={ano} mes={mes}"
        )
    if "ICTT" not in df.columns or "municipio" not in df.columns:
        raise PostgisUnavailableError("ictt_colunas_insuficientes")

    months = list_ictt_pr_competencias_upto(ano_max=ano, mes_max=mes)
    if not months:
        raise PostgisUnavailableError("sem_competencias_ictt_postgis")

    evolution: list[dict[str, Any]] = []
    for ano_ref, mes_ref in months:
        try:
            month_df = fetch_ictt_pr_dataframe(ano=ano_ref, mes=mes_ref)
        except PostgisUnavailableError:
            continue
        if month_df.empty:
            continue
        evolution.append(_monthly_snapshot(month_df))

    if not evolution:
        raise PostgisUnavailableError("monthly_evolution_vazia")

    context = build_report_context(
        ano,
        mes,
        scope,
        ictt_df=df,
        monthly_evolution=evolution,
    )
    errors = validate_report_context(context)
    # validate_report_context tem checks condicionais a 2026-04; lista vazia = OK.
    if errors:
        raise PostgisUnavailableError(f"contexto_invalido: {'; '.join(errors)}")

    summary = context.get("summary") or {}
    if int(summary.get("municipios_total") or 0) < MIN_EXPECTED_ROWS:
        raise PostgisUnavailableError("contexto_sem_municipios")

    competencia_str = str(
        context.get("metadata", {}).get("competencia_str") or f"{ano}-{mes:02d}"
    )
    markdown = render_report_context_markdown(context)

    return {
        "scope": scope,
        "ano": ano,
        "mes": mes,
        "competencia_str": competencia_str,
        "source": "deterministic_context",
        "uses_ai": False,
        "cache_status": "generated",
        "context": context,
        "markdown": markdown,
    }


def get_report_context(scope: str, ano: int, mes: int) -> GoldFetchResult:
    """Retorna report-context com headers de observabilidade Gold."""
    scope_key = (scope or "").strip().lower()
    backend = _configured_backend()

    if backend == "filesystem":
        payload = _filesystem_payload(scope_key, ano, mes)
        return GoldFetchResult(
            payload=payload,
            gold_backend="filesystem",
            data_source="filesystem",
            fallback_used=False,
        )

    # GOLD_BACKEND=postgis
    if scope_key != "pr":
        # Escopo não suportado no PostGIS: filesystem esperado (não é fallback real).
        # Na prática routes_ict já rejeita scope != pr com 400.
        payload = _filesystem_payload(scope_key, ano, mes)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="filesystem",
            fallback_used=False,
        )

    try:
        payload = _build_postgis_payload(scope_key, ano, mes)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="postgis",
            fallback_used=False,
        )
    except PostgisUnavailableError as exc:
        _log_and_record_fallback(
            scope=scope_key, ano=ano, mes=mes, reason=exc.reason
        )
        payload = _filesystem_payload(scope_key, ano, mes)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="fallback_filesystem",
            fallback_used=True,
        )
    except Exception as exc:  # noqa: BLE001
        _log_and_record_fallback(
            scope=scope_key, ano=ano, mes=mes, reason=f"exception: {exc}"
        )
        payload = _filesystem_payload(scope_key, ano, mes)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="fallback_filesystem",
            fallback_used=True,
        )
