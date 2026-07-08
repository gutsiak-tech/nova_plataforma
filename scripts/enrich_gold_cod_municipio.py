#!/usr/bin/env python3
"""CLI pontual: enriquecimento de cod_municipio em uma competencia Gold.

Delega para pipelines.gold.enrich_cod_municipio (modulo reutilizavel).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.core.config import PROJECT_ROOT
from pipelines.gold.enrich_cod_municipio import run_enrich_cod_municipio


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Enriquece Gold territorial com cod_municipio a partir dos GeoJSONs."
    )
    p.add_argument("--ano", type=int, default=2026)
    p.add_argument("--mes", type=int, default=4)
    p.add_argument(
        "--gold-root",
        default=str(PROJECT_ROOT / "data-lake" / "gold" / "caged"),
    )
    p.add_argument(
        "--geo-pr",
        default=str(PROJECT_ROOT / "dashboard" / "public" / "geo" / "municipios_pr.geojson"),
    )
    p.add_argument(
        "--geo-rmc",
        default=str(PROJECT_ROOT / "dashboard" / "public" / "geo" / "municipios_rmc.geojson"),
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--backup", action="store_true")
    p.add_argument("--strict", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_enrich_cod_municipio(
            ano=args.ano,
            mes=args.mes,
            gold_root=Path(args.gold_root),
            geo_pr=Path(args.geo_pr),
            geo_rmc=Path(args.geo_rmc),
            dry_run=args.dry_run,
            backup=args.backup,
            strict=args.strict,
        )
    except Exception as exc:
        print(f"ERRO: {exc}")
        return 1
    if args.strict and not result.get("ok", False):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
