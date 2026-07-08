#!/usr/bin/env python3
"""Backfill PostGIS de fatos Gold para multiplas competencias.

Usa pipelines.gold.load_fact_tables.load_dataset (sem duplicar logica).
Nao cria GOLD_BACKEND, nao altera API/frontend/mapas/Tegola.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pipelines.gold.load_fact_tables import DATASET_FILES, load_dataset  # noqa: E402

DEFAULT_DATASETS = ("municipio-pr", "municipio-rmc", "uf", "ictt-pr")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Backfill PostGIS (fatos) para multiplas competencias Gold."
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
        "--datasets",
        nargs="+",
        default=list(DEFAULT_DATASETS),
        choices=sorted(DATASET_FILES.keys()),
        help="Datasets de fato a carregar.",
    )
    p.add_argument(
        "--validate",
        action="store_true",
        help="Apos cada competencia, roda validate_postgis_vs_gold.py --scope all.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas imprime o plano; nao escreve no banco.",
    )
    p.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continua se uma competencia/dataset falhar.",
    )
    return p


def run_validation(ano: int, mes: int) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(_PROJECT_ROOT / "scripts" / "validate_postgis_vs_gold.py"),
        "--ano",
        str(ano),
        "--mes",
        str(mes),
        "--scope",
        "all",
    ]
    proc = subprocess.run(cmd, cwd=str(_PROJECT_ROOT), capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0
    # extrai linha de resumo se existir
    summary = ""
    for line in output.splitlines():
        if line.startswith("OK=") and "FAIL=" in line:
            summary = line.strip()
    if not summary:
        summary = f"exit={proc.returncode}"
    status = "OK" if ok else "FAIL"
    if ok and "WARN=" in summary and "WARN=0" not in summary:
        status = "WARN"
    return ok, f"{status} ({summary})"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ano = args.ano
    meses = sorted(set(int(m) for m in args.meses))
    datasets = list(args.datasets)

    for mes in meses:
        if not (1 <= mes <= 12):
            print(f"ERRO: mes invalido: {mes}")
            return 1

    print(
        f"Backfill PostGIS facts | ano={ano} meses={meses} datasets={datasets} "
        f"| dry_run={args.dry_run} validate={args.validate} "
        f"continue_on_error={args.continue_on_error}"
    )
    print("")

    failed = False
    summaries: list[dict[str, Any]] = []

    for mes in meses:
        comp = f"{ano}-{mes:02d}"
        print("=" * 60)
        print(f"COMPETENCIA {comp}")
        print("=" * 60)
        comp_ok = True
        dataset_rows: list[dict[str, Any]] = []

        for dataset in datasets:
            cmd_show = (
                f"python -m pipelines.gold.load_fact_tables "
                f"--dataset {dataset} --ano {ano} --mes {mes}"
            )
            if args.dry_run:
                print(f"[DRY-RUN] {cmd_show}")
                dataset_rows.append(
                    {
                        "dataset": dataset,
                        "ok": True,
                        "dry_run": True,
                        "command": cmd_show,
                        "upserted": None,
                    }
                )
                continue

            print(f"[RUN] {cmd_show}")
            try:
                report = load_dataset(dataset, ano=ano, mes=mes)
                upserted = report.get("upserted")
                ignored = report.get("ignored_non_territorial")
                print(
                    f"[OK] {dataset} upserted={upserted} "
                    f"ignored_non_territorial={ignored}"
                )
                dataset_rows.append(
                    {
                        "dataset": dataset,
                        "ok": True,
                        "dry_run": False,
                        "command": cmd_show,
                        "upserted": upserted,
                        "ignored_non_territorial": ignored,
                        "rows_read": report.get("rows_read"),
                    }
                )
            except Exception as exc:
                failed = True
                comp_ok = False
                print(f"[FAIL] {dataset} - {exc}")
                dataset_rows.append(
                    {
                        "dataset": dataset,
                        "ok": False,
                        "dry_run": False,
                        "command": cmd_show,
                        "error": str(exc),
                    }
                )
                if not args.continue_on_error:
                    print("Parando backfill (use --continue-on-error para seguir).")
                    summaries.append(
                        {
                            "competencia": comp,
                            "ok": False,
                            "datasets": dataset_rows,
                            "validation": None,
                        }
                    )
                    _print_summary(summaries)
                    return 1

        validation_status = None
        if args.validate:
            if args.dry_run:
                val_cmd = (
                    f"python scripts/validate_postgis_vs_gold.py "
                    f"--ano {ano} --mes {mes} --scope all"
                )
                print(f"[DRY-RUN] {val_cmd}")
                validation_status = "DRY-RUN"
            else:
                print(f"[VALIDATE] {comp}")
                ok, detail = run_validation(ano, mes)
                print(f"[VALIDATE] {comp} -> {detail}")
                validation_status = detail
                if not ok:
                    failed = True
                    comp_ok = False
                    if not args.continue_on_error:
                        summaries.append(
                            {
                                "competencia": comp,
                                "ok": False,
                                "datasets": dataset_rows,
                                "validation": validation_status,
                            }
                        )
                        _print_summary(summaries)
                        return 1

        summaries.append(
            {
                "competencia": comp,
                "ok": comp_ok and (
                    validation_status is None
                    or str(validation_status).startswith("OK")
                    or validation_status == "DRY-RUN"
                    or str(validation_status).startswith("WARN")
                ),
                "datasets": dataset_rows,
                "validation": validation_status,
            }
        )
        print("")

    _print_summary(summaries)
    if failed:
        print("RESULTADO: backfill com falhas. exit=1")
        return 1
    mode = "dry-run OK" if args.dry_run else "aplicacao OK"
    print(f"RESULTADO: {mode}. exit=0")
    return 0


def _print_summary(summaries: list[dict[str, Any]]) -> None:
    print("=" * 60)
    print("RESUMO BACKFILL POSTGIS")
    print("=" * 60)
    for item in summaries:
        status = "OK" if item.get("ok") else "FAIL"
        print(f"[{status}] {item['competencia']}")
        for ds in item.get("datasets") or []:
            if ds.get("dry_run"):
                print(f"  {ds['dataset']}: DRY-RUN ({ds['command']})")
            elif ds.get("ok"):
                print(
                    f"  {ds['dataset']}: OK upserted={ds.get('upserted')} "
                    f"ignored={ds.get('ignored_non_territorial')}"
                )
            else:
                print(f"  {ds['dataset']}: FAIL {ds.get('error')}")
        if item.get("validation") is not None:
            print(f"  validate: {item['validation']}")
    print("")


if __name__ == "__main__":
    raise SystemExit(main())
