"""Orquestrador Gold: filesystem | postgis com fallback explícito."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.config import API_LOG_FILE, GOLD_BACKEND, resolve_gold_backend
from app.core.fallback_registry import record_fallback
from app.core.logging import setup_logger
from app.repositories import gold_filesystem_repository as fs_repo
from app.repositories import gold_postgis_repository as pg_repo
from app.repositories.gold_postgis_repository import PostgisUnavailableError
from app.services.gold_service import GoldMonthRef, Scope

logger = setup_logger("api.gold.repository", API_LOG_FILE)

DataSource = Literal["filesystem", "postgis", "fallback_filesystem"]


@dataclass(frozen=True)
class GoldFetchResult:
    payload: dict[str, Any]
    gold_backend: str
    data_source: DataSource
    fallback_used: bool

    def observability_headers(self) -> dict[str, str]:
        return {
            "X-Gold-Backend": self.gold_backend,
            "X-Data-Source": self.data_source,
            "X-Fallback-Used": "true" if self.fallback_used else "false",
        }


def _configured_backend() -> str:
    # Reavalia env em runtime (útil em testes); default seguro.
    try:
        return resolve_gold_backend()
    except Exception:  # noqa: BLE001
        return GOLD_BACKEND if GOLD_BACKEND in {"filesystem", "postgis"} else "filesystem"


def _log_fallback(
    *,
    endpoint: str,
    table_name: str | None,
    scope: Scope,
    month: GoldMonthRef,
    reason: str,
) -> None:
    logger.warning(
        "[DATA_SOURCE] fallback usado | endpoint=%s | table_name=%s | scope=%s | "
        "ano=%s | mes=%s | motivo=%s",
        endpoint,
        table_name,
        scope,
        month.ano,
        month.mes,
        reason,
    )
    # Contador operacional: apenas fallback real (não filesystem esperado).
    record_fallback(
        endpoint=endpoint,
        table_name=table_name,
        scope=scope,
        ano=month.ano,
        mes=month.mes,
        reason=reason,
    )


def get_table(
    month: GoldMonthRef,
    *,
    base_name: str,
    scope: Scope,
    limit: int,
    offset: int,
    sort_by: str | None,
    sort_dir: str,
) -> GoldFetchResult:
    backend = _configured_backend()

    if backend == "filesystem":
        payload = fs_repo.build_table_payload(
            month,
            base_name=base_name,
            scope=scope,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return GoldFetchResult(
            payload=payload,
            gold_backend="filesystem",
            data_source="filesystem",
            fallback_used=False,
        )

    # GOLD_BACKEND=postgis
    if not pg_repo.is_table_supported(base_name, scope):
        payload = fs_repo.build_table_payload(
            month,
            base_name=base_name,
            scope=scope,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="filesystem",
            fallback_used=False,
        )

    try:
        payload = pg_repo.build_table_payload(
            month,
            base_name=base_name,
            scope=scope,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="postgis",
            fallback_used=False,
        )
    except PostgisUnavailableError as exc:
        _log_fallback(
            endpoint="/api/gold/v1/table",
            table_name=base_name,
            scope=scope,
            month=month,
            reason=exc.reason,
        )
        payload = fs_repo.build_table_payload(
            month,
            base_name=base_name,
            scope=scope,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="fallback_filesystem",
            fallback_used=True,
        )
    except Exception as exc:  # noqa: BLE001
        _log_fallback(
            endpoint="/api/gold/v1/table",
            table_name=base_name,
            scope=scope,
            month=month,
            reason=f"exception: {exc}",
        )
        payload = fs_repo.build_table_payload(
            month,
            base_name=base_name,
            scope=scope,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="fallback_filesystem",
            fallback_used=True,
        )


def get_overview(month: GoldMonthRef, *, scope: Scope) -> GoldFetchResult:
    backend = _configured_backend()

    if backend == "filesystem":
        payload = fs_repo.build_overview_payload(month, scope=scope)
        return GoldFetchResult(
            payload=payload,
            gold_backend="filesystem",
            data_source="filesystem",
            fallback_used=False,
        )

    if not pg_repo.is_overview_supported(scope):
        payload = fs_repo.build_overview_payload(month, scope=scope)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="filesystem",
            fallback_used=False,
        )

    try:
        payload = pg_repo.build_overview_payload(month, scope=scope)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="postgis",
            fallback_used=False,
        )
    except PostgisUnavailableError as exc:
        _log_fallback(
            endpoint="/api/gold/v1/overview",
            table_name=None,
            scope=scope,
            month=month,
            reason=exc.reason,
        )
        payload = fs_repo.build_overview_payload(month, scope=scope)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="fallback_filesystem",
            fallback_used=True,
        )
    except Exception as exc:  # noqa: BLE001
        _log_fallback(
            endpoint="/api/gold/v1/overview",
            table_name=None,
            scope=scope,
            month=month,
            reason=f"exception: {exc}",
        )
        payload = fs_repo.build_overview_payload(month, scope=scope)
        return GoldFetchResult(
            payload=payload,
            gold_backend="postgis",
            data_source="fallback_filesystem",
            fallback_used=True,
        )
