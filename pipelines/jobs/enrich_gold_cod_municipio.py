"""Job CLI: enriquecimento de cod_municipio para uma competencia Gold."""

from __future__ import annotations

import argparse

from app.core.config import DEFAULT_ANO, DEFAULT_MES, PIPELINE_LOG_FILE
from app.core.logging import setup_logger
from app.services.gold_service import resolve_gold_month
from pipelines.gold.enrich_cod_municipio import run_enrich_cod_municipio

logger = setup_logger("job_enrich_cod_municipio", PIPELINE_LOG_FILE)


def run_job(
    ano: int = DEFAULT_ANO,
    mes: int = DEFAULT_MES,
    *,
    dry_run: bool = False,
    backup: bool = False,
    strict: bool = False,
) -> dict:
    logger.info(
        "[JOB] enrich_cod_municipio | ano=%s mes=%s dry_run=%s backup=%s strict=%s",
        ano,
        mes,
        dry_run,
        backup,
        strict,
    )
    result = run_enrich_cod_municipio(
        ano=ano,
        mes=mes,
        dry_run=dry_run,
        backup=backup,
        strict=strict,
        diagnose_national=False,
    )
    if strict and not result.get("ok", False):
        raise RuntimeError(
            f"enrich_cod_municipio strict falhou para {ano}-{mes:02d}: "
            "municipio real sem match."
        )
    logger.info("[JOB] enrich_cod_municipio concluido | ano=%s mes=%02d", ano, mes)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enriquece cod_municipio nas tabelas Gold territoriais (PR/RMC/ICTT)."
    )
    parser.add_argument("--ano", type=int, default=None)
    parser.add_argument("--mes", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    month = resolve_gold_month(ano=args.ano, mes=args.mes)
    run_job(
        ano=month.ano,
        mes=month.mes,
        dry_run=args.dry_run,
        backup=args.backup,
        strict=args.strict,
    )
