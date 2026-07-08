from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pipelines.gold.compute_ict_report_context import (
    SCOPE_UNSUPPORTED_MSG,
    SUPPORTED_SCOPES,
    build_report_context,
    report_context_dir,
    save_report_context,
)

CacheStatus = Literal["hit", "generated"]

REPORT_SCOPE_UNSUPPORTED_MSG = (
    "O relatório do ICT está disponível inicialmente apenas para o escopo Paraná."
)


def report_json_path(ano: int, mes: int, scope: str) -> Path:
    return report_context_dir(ano, mes) / f"ict_report_context_{scope}.json"


def report_markdown_path(ano: int, mes: int, scope: str) -> Path:
    return report_context_dir(ano, mes) / f"ict_report_context_{scope}.md"


def _ensure_supported_scope(scope: str) -> str:
    scope_key = (scope or "").strip().lower()
    if scope_key not in SUPPORTED_SCOPES:
        raise ValueError(REPORT_SCOPE_UNSUPPORTED_MSG)
    return scope_key


def load_report_context_json(ano: int, mes: int, scope: str) -> dict[str, Any]:
    path = report_json_path(ano, mes, scope)
    if not path.is_file():
        raise FileNotFoundError(
            f"Contexto analítico do ICT não encontrado para {scope} em {ano}-{mes:02d}."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def get_or_build_ict_report_payload(scope: str, ano: int, mes: int) -> dict[str, Any]:
    scope_key = _ensure_supported_scope(scope)
    json_path = report_json_path(ano, mes, scope_key)
    cache_status: CacheStatus

    if json_path.is_file():
        context = load_report_context_json(ano, mes, scope_key)
        cache_status = "hit"
    else:
        context = build_report_context(ano, mes, scope_key)
        save_report_context(context, ano, mes, scope_key)
        cache_status = "generated"

    markdown: str | None = None
    md_path = report_markdown_path(ano, mes, scope_key)
    if md_path.is_file():
        markdown = md_path.read_text(encoding="utf-8")

    competencia_str = str(context.get("metadata", {}).get("competencia_str") or f"{ano}-{mes:02d}")

    return {
        "scope": scope_key,
        "ano": ano,
        "mes": mes,
        "competencia_str": competencia_str,
        "source": "deterministic_context",
        "uses_ai": False,
        "cache_status": cache_status,
        "context": context,
        "markdown": markdown,
    }


def validate_scope_for_report(scope: str) -> None:
    _ensure_supported_scope(scope)
