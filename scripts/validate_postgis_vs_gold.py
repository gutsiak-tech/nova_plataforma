#!/usr/bin/env python3
"""Validação não destrutiva Gold filesystem × PostGIS.

Compara somas e contagens para municipio-pr, municipio-rmc, uf e ictt-pr.
Não altera dados. Usa POSTGRES_* de app.core.config.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.core.config import GOLD_CAGED_DIR  # noqa: E402
from app.db.connection import get_connection  # noqa: E402
from pipelines.gold.load_fact_tables import (  # noqa: E402
    SPECIAL_NON_MUNICIPIO,
    format_cod_municipio,
    normalize_key,
    resolve_uf_sigla,
)

FLOAT_TOL = 1e-6
INT_TOL = 0


class Runner:
    def __init__(self) -> None:
        self.ok = 0
        self.warn = 0
        self.fail = 0

    def record(self, level: str, name: str, detail: str) -> None:
        print(f"[{level}] {name} - {detail}")
        if level == "OK":
            self.ok += 1
        elif level == "WARN":
            self.warn += 1
        else:
            self.fail += 1


def read_gold(ano: int, mes: int, base: str) -> pd.DataFrame:
    folder = GOLD_CAGED_DIR / f"ano={ano}" / f"mes={mes:02d}"
    parquet = folder / f"{base}.parquet"
    csv = folder / f"{base}.csv"
    if parquet.is_file():
        return pd.read_parquet(parquet)
    if csv.is_file():
        return pd.read_csv(csv)
    raise FileNotFoundError(f"Gold ausente: {base}")


def pg_fetchone(sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...] | None:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def nearly_equal(a: float | None, b: float | None, *, tol: float) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if math.isnan(a) and math.isnan(b):
        return True
    return abs(float(a) - float(b)) <= tol


def filter_real_municipios(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "municipio" in out.columns:
        mask = out["municipio"].map(
            lambda v: normalize_key(v) not in SPECIAL_NON_MUNICIPIO
            and normalize_key(v) is not None
        )
        out = out[mask]
    if "cod_municipio" in out.columns:
        out = out[out["cod_municipio"].map(lambda v: format_cod_municipio(v) is not None)]
    return out


def sum_cols(df: pd.DataFrame, cols: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for c in cols:
        if c not in df.columns:
            result[c] = 0.0
            continue
        result[c] = float(pd.to_numeric(df[c], errors="coerce").fillna(0).sum())
    return result


def validate_municipio(
    runner: Runner,
    *,
    scope: str,
    ano: int,
    mes: int,
) -> None:
    table = "tabela_municipio_pr" if scope == "pr" else "tabela_municipio_rmc"
    label = f"municipio-{scope}"
    gold = filter_real_municipios(read_gold(ano, mes, table))
    g_sums = sum_cols(gold, ["admissoes", "desligamentos", "saldo"])
    g_count = len(gold)

    # Compara apenas pelos cod_municipio da Gold (evita resíduos de loads legados
    # no PostGIS com malha completa / competências misturadas).
    codes = [
        format_cod_municipio(v)
        for v in gold["cod_municipio"].tolist()
        if format_cod_municipio(v)
    ]
    if not codes:
        runner.record("FAIL", label, "Gold sem cod_municipio carregável")
        return

    row = pg_fetchone(
        """
        SELECT COUNT(*), COALESCE(SUM(admissoes),0), COALESCE(SUM(desligamentos),0),
               COALESCE(SUM(saldo),0)
        FROM serving.fact_emprego_municipio_mes
        WHERE ano = %s AND mes = %s AND cod_municipio = ANY(%s)
        """,
        (ano, mes, codes),
    )
    if row is None:
        runner.record("FAIL", label, "sem retorno PostGIS")
        return
    p_count, p_adm, p_des, p_sal = int(row[0]), float(row[1]), float(row[2]), float(row[3])

    checks = [
        ("count", float(g_count), float(p_count), INT_TOL),
        ("admissoes", g_sums["admissoes"], p_adm, INT_TOL),
        ("desligamentos", g_sums["desligamentos"], p_des, INT_TOL),
        ("saldo", g_sums["saldo"], p_sal, INT_TOL),
    ]
    for name, g, p, tol in checks:
        if nearly_equal(g, p, tol=tol):
            runner.record("OK", f"{label}/{name}", f"gold={g} postgis={p}")
        else:
            runner.record("FAIL", f"{label}/{name}", f"gold={g} postgis={p}")


def validate_uf(runner: Runner, *, ano: int, mes: int) -> None:
    gold = read_gold(ano, mes, "tabela_uf")
    # somente UFs com sigla válida
    mask = gold["uf"].map(lambda v: resolve_uf_sigla(v) is not None)
    gold = gold[mask]
    g_sums = sum_cols(gold, ["admissoes", "desligamentos", "saldo"])
    g_count = len(gold)

    # Compara apenas pelas siglas presentes na Gold (evita resíduos legados
    # no PostGIS, ex.: UF "NI", que o loader atual não grava nem apaga).
    siglas = sorted(
        {
            resolve_uf_sigla(v)
            for v in gold["uf"].tolist()
            if resolve_uf_sigla(v) is not None
        }
    )
    if not siglas:
        runner.record("FAIL", "uf", "Gold sem UF carregável")
        return

    row = pg_fetchone(
        """
        SELECT COUNT(*), COALESCE(SUM(admissoes),0), COALESCE(SUM(desligamentos),0),
               COALESCE(SUM(saldo),0)
        FROM serving.fact_emprego_uf_mes
        WHERE ano = %s AND mes = %s AND uf = ANY(%s)
        """,
        (ano, mes, siglas),
    )
    if row is None:
        runner.record("FAIL", "uf", "sem retorno PostGIS")
        return
    p_count, p_adm, p_des, p_sal = int(row[0]), float(row[1]), float(row[2]), float(row[3])
    checks = [
        ("count", float(g_count), float(p_count), INT_TOL),
        ("admissoes", g_sums["admissoes"], p_adm, INT_TOL),
        ("desligamentos", g_sums["desligamentos"], p_des, INT_TOL),
        ("saldo", g_sums["saldo"], p_sal, INT_TOL),
    ]
    for name, g, p, tol in checks:
        if nearly_equal(g, p, tol=tol):
            runner.record("OK", f"uf/{name}", f"gold={g} postgis={p}")
        else:
            runner.record("FAIL", f"uf/{name}", f"gold={g} postgis={p}")


def validate_ictt(runner: Runner, *, ano: int, mes: int) -> None:
    gold = read_gold(ano, mes, "tabela_ictt_municipio_pr")
    gold = gold[gold["cod_municipio"].map(lambda v: format_cod_municipio(v) is not None)]
    g_count = len(gold)
    g_with = gold["ICTT"].notna().sum() if "ICTT" in gold.columns else 0
    g_mean = float(pd.to_numeric(gold["ICTT"], errors="coerce").mean()) if g_with else None
    g_min = float(pd.to_numeric(gold["ICTT"], errors="coerce").min()) if g_with else None
    g_max = float(pd.to_numeric(gold["ICTT"], errors="coerce").max()) if g_with else None

    row = pg_fetchone(
        """
        SELECT COUNT(*),
               COUNT("ICTT"),
               AVG("ICTT"),
               MIN("ICTT"),
               MAX("ICTT")
        FROM serving.fact_ictt_municipio_pr_mes
        WHERE ano = %s AND mes = %s
          AND cod_municipio IS NOT NULL
        """,
        (ano, mes),
    )
    if row is None:
        runner.record("FAIL", "ictt-pr", "sem retorno PostGIS")
        return
    p_count, p_with, p_mean, p_min, p_max = (
        int(row[0]),
        int(row[1] or 0),
        float(row[2]) if row[2] is not None else None,
        float(row[3]) if row[3] is not None else None,
        float(row[4]) if row[4] is not None else None,
    )

    if g_count == p_count:
        runner.record("OK", "ictt-pr/count", f"gold={g_count} postgis={p_count}")
    else:
        runner.record("FAIL", "ictt-pr/count", f"gold={g_count} postgis={p_count}")

    if int(g_with) == p_with:
        runner.record("OK", "ictt-pr/with_ictt", f"gold={g_with} postgis={p_with}")
    else:
        runner.record("FAIL", "ictt-pr/with_ictt", f"gold={g_with} postgis={p_with}")

    for name, g, p in (("mean", g_mean, p_mean), ("min", g_min, p_min), ("max", g_max, p_max)):
        if nearly_equal(g, p, tol=FLOAT_TOL):
            runner.record("OK", f"ictt-pr/{name}", f"gold={g} postgis={p}")
        else:
            # média pode variar ligeiramente; WARN se próximo
            if g is not None and p is not None and abs(g - p) < 1e-3:
                runner.record("WARN", f"ictt-pr/{name}", f"gold={g} postgis={p}")
            else:
                runner.record("FAIL", f"ictt-pr/{name}", f"gold={g} postgis={p}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida Gold × PostGIS.")
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--mes", type=int, default=4)
    parser.add_argument(
        "--scope",
        default="all",
        choices=["pr", "rmc", "br", "ictt-pr", "all"],
    )
    args = parser.parse_args(argv)
    runner = Runner()
    print(f"Validate Gold x PostGIS | {args.ano}-{args.mes:02d} | scope={args.scope}")
    print("")

    try:
        get_connection().close()
    except Exception as exc:
        print(f"[FAIL] database - indisponivel: {exc}")
        return 1

    scopes = [args.scope] if args.scope != "all" else ["pr", "rmc", "br", "ictt-pr"]
    try:
        if "pr" in scopes:
            validate_municipio(runner, scope="pr", ano=args.ano, mes=args.mes)
        if "rmc" in scopes:
            validate_municipio(runner, scope="rmc", ano=args.ano, mes=args.mes)
        if "br" in scopes:
            validate_uf(runner, ano=args.ano, mes=args.mes)
        if "ictt-pr" in scopes:
            validate_ictt(runner, ano=args.ano, mes=args.mes)
    except Exception as exc:
        runner.record("FAIL", "exception", str(exc))

    print("")
    print(f"OK={runner.ok} WARN={runner.warn} FAIL={runner.fail}")
    return 0 if runner.fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
