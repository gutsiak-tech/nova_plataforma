#!/usr/bin/env python3
"""Backfill seguro de cod_municipio para varias competencias Gold.

Chama pipelines.gold.enrich_cod_municipio competencia por competencia.
Nao altera frontend, PostGIS, Tegola nem contratos da API.
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
        description="Backfill multi-competencia de cod_municipio na Gold territorial."
    )
    p.add_argument("--ano", type=int, default=2026)
    p.add_argument(
        "--meses",
        type=int,
        nargs="+",
        default=[1, 2, 3, 4],
        help="Lista de meses (ex.: 1 2 3 4).",
    )
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
    ano = args.ano
    meses = sorted(set(int(m) for m in args.meses))
    for mes in meses:
        if not (1 <= mes <= 12):
            print(f"ERRO: mes invalido: {mes}")
            return 1

    print(
        f"Backfill cod_municipio | ano={ano} meses={meses} "
        f"| dry_run={args.dry_run} backup={args.backup} strict={args.strict}"
    )
    print("")

    summaries: list[dict] = []
    failed = False

    for mes in meses:
        print("=" * 60)
        print(f"COMPETENCIA {ano}-{mes:02d}")
        print("=" * 60)
        try:
            result = run_enrich_cod_municipio(
                ano=ano,
                mes=mes,
                gold_root=Path(args.gold_root),
                geo_pr=Path(args.geo_pr),
                geo_rmc=Path(args.geo_rmc),
                dry_run=args.dry_run,
                backup=args.backup,
                strict=args.strict,
                diagnose_national=False,
            )
        except Exception as exc:
            print(f"ERRO competencia {ano}-{mes:02d}: {exc}")
            failed = True
            summaries.append(
                {
                    "ano": ano,
                    "mes": mes,
                    "ok": False,
                    "error": str(exc),
                    "tables": [],
                }
            )
            if args.strict:
                print("Parando backfill (--strict).")
                break
            continue

        ok = bool(result.get("ok", False)) if args.strict else True
        if args.strict and not ok:
            failed = True
            summaries.append(
                {
                    "ano": ano,
                    "mes": mes,
                    "ok": False,
                    "tables": result.get("tables", []),
                }
            )
            print("Parando backfill (--strict: municipio real sem match).")
            break

        summaries.append(
            {
                "ano": ano,
                "mes": mes,
                "ok": True,
                "tables": result.get("tables", []),
            }
        )
        print("")

    print("=" * 60)
    print("RESUMO BACKFILL")
    print("=" * 60)
    for item in summaries:
        comp = f"{item['ano']}-{item['mes']:02d}"
        status = "OK" if item.get("ok") else "FAIL"
        print(f"[{status}] {comp}")
        if item.get("error"):
            print(f"  erro: {item['error']}")
            continue
        for table in item.get("tables") or []:
            name = table.get("table")
            print(
                f"  {name}: filled {table.get('before_filled')}->"
                f"{table.get('after_filled')}/{table.get('rows')} "
                f"(+{table.get('filled_this_run')}) "
                f"ignorado={table.get('ignored_rows')} "
                f"unmatched_real={len(table.get('unmatched_real') or [])}"
            )
    print("")

    if failed:
        print("RESULTADO: backfill com falhas. exit=1")
        return 1
    mode = "dry-run OK" if args.dry_run else "aplicacao OK"
    print(f"RESULTADO: {mode}. exit=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
