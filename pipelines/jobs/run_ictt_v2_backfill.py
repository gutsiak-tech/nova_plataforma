"""
Backfill do ICTT v2.0 na Gold versionada.

Não chama compute_ictt (V1). Não grava tabela_ictt_municipio_pr.
Nesta primeira rodada o intervalo padrão é 2026-01..2026-04.
Competências posteriores são apenas reportadas.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import PIPELINE_LOG_FILE, SILVER_CAGED_DIR
from app.core.logging import setup_logger
from pipelines.gold.compute_ictt_v2 import (
    OUTPUT_STEM,
    compute_ictt_v2,
    gold_v2_parquet_path,
    v1_gold_parquet_path,
)

logger = setup_logger("job_ictt_v2_backfill", PIPELINE_LOG_FILE)

SILVER_PARQUET_NAME = "caged_tratado.parquet"
COMPETENCIA_RE = re.compile(r"^(\d{4})-(\d{2})$")
DEFAULT_START = "2026-01"
DEFAULT_END = "2026-04"


@dataclass(frozen=True)
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


@dataclass
class BackfillResult:
    competencia: str
    status: str
    message: str = ""
    n_rows: int = 0
    n_ictt: int = 0


@dataclass
class BackfillSummary:
    dry_run: bool
    overwrite: bool
    results: list[BackfillResult] = field(default_factory=list)
    later_competencies: list[str] = field(default_factory=list)


def list_silver_competencies() -> list[CompetenciaRef]:
    found: list[CompetenciaRef] = []
    if not SILVER_CAGED_DIR.exists():
        return found
    for ano_dir in sorted(SILVER_CAGED_DIR.glob("ano=*")):
        try:
            ano = int(ano_dir.name.split("=", 1)[1])
        except (IndexError, ValueError):
            continue
        for mes_dir in sorted(ano_dir.glob("mes=*")):
            try:
                mes = int(mes_dir.name.split("=", 1)[1])
            except (IndexError, ValueError):
                continue
            if not (1 <= mes <= 12):
                continue
            parquet = mes_dir / SILVER_PARQUET_NAME
            if parquet.is_file():
                found.append(CompetenciaRef(ano=ano, mes=mes))
    return found


def parse_competencia(label: str) -> tuple[int, int]:
    match = COMPETENCIA_RE.fullmatch(label.strip())
    if not match:
        raise ValueError(f"competência inválida: {label!r}. Use YYYY-MM.")
    return int(match.group(1)), int(match.group(2))


def _in_range(item: CompetenciaRef, start: str, end: str) -> bool:
    start_t = parse_competencia(start)
    end_t = parse_competencia(end)
    return start_t <= (item.ano, item.mes) <= end_t


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_backfill(
    *,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    dry_run: bool = False,
    overwrite: bool = True,
) -> BackfillSummary:
    all_competencies = list_silver_competencies()
    selected = [item for item in all_competencies if _in_range(item, start, end)]
    later = [
        item.label
        for item in all_competencies
        if parse_competencia(item.label) > parse_competencia(end)
    ]
    summary = BackfillSummary(
        dry_run=dry_run, overwrite=overwrite, later_competencies=later
    )

    if later:
        logger.info(
            "Competências Silver posteriores a %s (não backfilladas nesta rodada): %s",
            end,
            ", ".join(later),
        )

    if not selected:
        logger.error("Nenhuma competência Silver no intervalo %s..%s", start, end)
        return summary

    for item in selected:
        out_path = gold_v2_parquet_path(item.ano, item.mes)
        v1_path = v1_gold_parquet_path(item.ano, item.mes)
        v1_hash_before = file_sha256(v1_path) if v1_path.is_file() else None

        if out_path.is_file() and not overwrite:
            msg = f"saída existente: {out_path}"
            logger.info("Pulando %s | %s", item.label, msg)
            summary.results.append(
                BackfillResult(competencia=item.label, status="skipped", message=msg)
            )
            continue

        if dry_run:
            action = "substituir" if out_path.is_file() else "gerar"
            msg = f"{action} {out_path}"
            logger.info("[dry-run] %s | %s", item.label, msg)
            summary.results.append(
                BackfillResult(
                    competencia=item.label, status="ok", message=f"dry-run: {msg}"
                )
            )
            continue

        df = compute_ictt_v2(ano=item.ano, mes=item.mes, persist=True)
        n_ictt = int(df["ictt_v2"].notna().sum())
        if v1_path.is_file() and v1_hash_before is not None:
            v1_hash_after = file_sha256(v1_path)
            if v1_hash_after != v1_hash_before:
                raise RuntimeError(
                    f"IMPLEMENTACAO_V2_BLOQUEADA: artefato V1 alterado em {v1_path}"
                )

        summary.results.append(
            BackfillResult(
                competencia=item.label,
                status="ok",
                message=str(out_path),
                n_rows=len(df),
                n_ictt=n_ictt,
            )
        )
        logger.info(
            "ICTT v2 backfill | %s | rows=%s | ictt=%s | %s",
            item.label,
            len(df),
            n_ictt,
            out_path,
        )

    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Gold do ICTT v2.0.")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Não substitui competência V2 já persistida.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = run_backfill(
        start=args.start,
        end=args.end,
        dry_run=args.dry_run,
        overwrite=not args.no_overwrite,
    )
    if not summary.results:
        print(
            f"ICTT v2 backfill | nenhuma competência no intervalo "
            f"{args.start}..{args.end}"
        )
        return 1
    ok = sum(1 for item in summary.results if item.status == "ok")
    print(
        f"ICTT v2 backfill | ok={ok}/{len(summary.results)} | "
        f"posteriores={summary.later_competencies or '-'}"
    )
    for item in summary.results:
        print(
            f"  {item.competencia} {item.status} rows={item.n_rows} "
            f"ictt={item.n_ictt} {item.message}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
