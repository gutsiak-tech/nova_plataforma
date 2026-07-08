"""
Backfill multi-competência do ICTT na camada Gold.

Lê competências disponíveis na Silver e invoca compute_ictt por partição.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import PIPELINE_LOG_FILE, SILVER_CAGED_DIR
from app.core.logging import setup_logger
from pipelines.gold.aggregate_indicators import gold_mes_dir
from pipelines.gold.compute_ictt import SCOPE_OUTPUT_STEM, compute_ictt

logger = setup_logger("job_ictt_backfill", PIPELINE_LOG_FILE)

SILVER_PARQUET_NAME = "caged_tratado.parquet"
COMPETENCIA_RE = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass
class CompetenciaRef:
    ano: int
    mes: int

    @property
    def label(self) -> str:
        return f"{self.ano}-{self.mes:02d}"

    @property
    def silver_parquet(self) -> Path:
        return (
            SILVER_CAGED_DIR
            / f"ano={self.ano}"
            / f"mes={self.mes:02d}"
            / SILVER_PARQUET_NAME
        )

    def ictt_parquet(self, scope: str) -> Path:
        stem = SCOPE_OUTPUT_STEM[scope]  # type: ignore[index]
        return gold_mes_dir(self.ano, self.mes) / f"{stem}.parquet"


@dataclass
class BackfillResult:
    competencia: str
    status: str
    message: str = ""
    calculados: int | None = None
    sem_dados: int | None = None


@dataclass
class BackfillSummary:
    scope: str
    dry_run: bool
    overwrite: bool
    results: list[BackfillResult] = field(default_factory=list)

    @property
    def ok(self) -> list[BackfillResult]:
        return [r for r in self.results if r.status == "ok"]

    @property
    def skipped(self) -> list[BackfillResult]:
        return [r for r in self.results if r.status == "skipped"]

    @property
    def failed(self) -> list[BackfillResult]:
        return [r for r in self.results if r.status == "error"]


def parse_competencia_str(value: str) -> CompetenciaRef:
    match = COMPETENCIA_RE.match(value.strip())
    if not match:
        raise ValueError(f"competência inválida: {value!r}. Use YYYY-MM.")
    ano = int(match.group(1))
    mes = int(match.group(2))
    if not (1 <= mes <= 12):
        raise ValueError(f"mês inválido em {value!r}.")
    return CompetenciaRef(ano=ano, mes=mes)


def list_silver_competencies() -> list[CompetenciaRef]:
    if not SILVER_CAGED_DIR.is_dir():
        return []

    found: list[CompetenciaRef] = []
    for ano_dir in sorted(SILVER_CAGED_DIR.glob("ano=*")):
        if not ano_dir.is_dir():
            continue
        try:
            ano = int(ano_dir.name.split("=", 1)[1])
        except ValueError:
            continue

        for mes_dir in sorted(ano_dir.glob("mes=*")):
            if not mes_dir.is_dir():
                continue
            try:
                mes = int(mes_dir.name.split("=", 1)[1])
            except ValueError:
                continue
            if not (1 <= mes <= 12):
                continue

            parquet = mes_dir / SILVER_PARQUET_NAME
            if parquet.is_file():
                found.append(CompetenciaRef(ano=ano, mes=mes))

    return sorted(found, key=lambda c: (c.ano, c.mes))


def filter_competencies(
    all_competencies: list[CompetenciaRef],
    *,
    ano: int | None,
    mes: int | None,
    start: str | None,
    end: str | None,
) -> list[CompetenciaRef]:
    if ano is not None and mes is not None:
        return [c for c in all_competencies if c.ano == ano and c.mes == mes]

    if ano is not None:
        return [c for c in all_competencies if c.ano == ano]

    if start is not None or end is not None:
        start_ref = parse_competencia_str(start or end or "")
        end_ref = parse_competencia_str(end or start or "")
        if (start_ref.ano, start_ref.mes) > (end_ref.ano, end_ref.mes):
            start_ref, end_ref = end_ref, start_ref
        return [
            c
            for c in all_competencies
            if (start_ref.ano, start_ref.mes) <= (c.ano, c.mes) <= (end_ref.ano, end_ref.mes)
        ]

    return list(all_competencies)


def run_ictt_backfill(
    *,
    scope: str = "pr",
    ano: int | None = None,
    mes: int | None = None,
    start: str | None = None,
    end: str | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
) -> BackfillSummary:
    scope_key = scope.lower().strip()
    if scope_key not in SCOPE_OUTPUT_STEM:
        raise ValueError(f"scope inválido: {scope!r}. Use: br | pr | rmc")

    all_competencies = list_silver_competencies()
    selected = filter_competencies(
        all_competencies,
        ano=ano,
        mes=mes,
        start=start,
        end=end,
    )

    summary = BackfillSummary(scope=scope_key, dry_run=dry_run, overwrite=overwrite)

    if not selected:
        logger.warning("Nenhuma competência Silver encontrada para os filtros informados.")
        return summary

    for competencia in selected:
        label = competencia.label
        output_path = competencia.ictt_parquet(scope_key)

        if output_path.is_file() and not overwrite:
            msg = f"saída existente: {output_path}"
            logger.info("Pulando %s | %s", label, msg)
            summary.results.append(BackfillResult(competencia=label, status="skipped", message=msg))
            continue

        if dry_run:
            action = "sobrescrever" if output_path.is_file() else "gerar"
            msg = f"{action} {output_path}"
            logger.info("[dry-run] %s | %s", label, msg)
            summary.results.append(BackfillResult(competencia=label, status="ok", message=f"dry-run: {msg}"))
            continue

        try:
            df = compute_ictt(ano=competencia.ano, mes=competencia.mes, scope=scope_key)
            status_counts = df["status_calculo"].value_counts().to_dict()
            calculados = int(status_counts.get("calculado", 0))
            sem_dados = int(status_counts.get("sem_dados_suficientes", 0))
            logger.info(
                "ICTT concluído | competencia=%s | calculados=%s | sem_dados=%s",
                label,
                calculados,
                sem_dados,
            )
            summary.results.append(
                BackfillResult(
                    competencia=label,
                    status="ok",
                    calculados=calculados,
                    sem_dados=sem_dados,
                )
            )
        except Exception as exc:
            logger.exception("Falha ICTT | competencia=%s", label)
            summary.results.append(
                BackfillResult(competencia=label, status="error", message=str(exc))
            )

    return summary


def print_backfill_summary(summary: BackfillSummary) -> None:
    print(f"\n=== Resumo backfill ICTT | scope={summary.scope} ===")
    print(f"dry_run={summary.dry_run} | overwrite={summary.overwrite}")
    print(f"Processadas com sucesso: {len(summary.ok)}")
    print(f"Puladas (já existiam): {len(summary.skipped)}")
    print(f"Com erro: {len(summary.failed)}")

    if summary.ok:
        print("\nSucesso:")
        for item in summary.ok:
            if item.calculados is not None:
                print(
                    f"  {item.competencia}: calculados={item.calculados}, "
                    f"sem_dados_suficientes={item.sem_dados}"
                )
            else:
                print(f"  {item.competencia}: {item.message}")

    if summary.skipped:
        print("\nPuladas:")
        for item in summary.skipped:
            print(f"  {item.competencia}: {item.message}")

    if summary.failed:
        print("\nErros:")
        for item in summary.failed:
            print(f"  {item.competencia}: {item.message}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa ICTT para múltiplas competências Silver na camada Gold.",
    )
    parser.add_argument(
        "--scope",
        type=str,
        default="pr",
        choices=sorted(SCOPE_OUTPUT_STEM.keys()),
        help="Recorte territorial (default: pr).",
    )
    parser.add_argument("--ano", type=int, default=None, help="Filtrar por ano.")
    parser.add_argument("--mes", type=int, default=None, help="Filtrar por mês (use com --ano).")
    parser.add_argument("--start", type=str, default=None, help="Competência inicial YYYY-MM.")
    parser.add_argument("--end", type=str, default=None, help="Competência final YYYY-MM.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recalcular mesmo quando a saída Gold já existir.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas listar o que seria executado.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.mes is not None and args.ano is None:
        raise SystemExit("--mes requer --ano.")

    summary = run_ictt_backfill(
        scope=args.scope,
        ano=args.ano,
        mes=args.mes,
        start=args.start,
        end=args.end,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )
    print_backfill_summary(summary)
    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
