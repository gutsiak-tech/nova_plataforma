"""Carga idempotente de fatos Gold → PostGIS.

Datasets:
  municipio-pr | municipio-rmc | uf | ictt-pr

Municipais exigem coluna cod_municipio (falha explícita se ausente).
IGNORADO é categoria não territorial e é ignorada na carga.
Não altera frontend, Tegola nem API Gold filesystem.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import (
    DEFAULT_ANO,
    DEFAULT_MES,
    GOLD_CAGED_DIR,
    PIPELINE_LOG_FILE,
    PROJECT_ROOT,
)
from app.core.logging import setup_logger
from app.db.connection import get_connection

logger = setup_logger("load_fact", PIPELINE_LOG_FILE)

SPECIAL_NON_MUNICIPIO = frozenset({"IGNORADO"})
PUNCT_RE = re.compile(r"[.,;:/\-_|]+")

UF_SIGLA_BY_NORM: dict[str, str] = {
    "ACRE": "AC",
    "ALAGOAS": "AL",
    "AMAPA": "AP",
    "AMAZONAS": "AM",
    "BAHIA": "BA",
    "CEARA": "CE",
    "DISTRITO FEDERAL": "DF",
    "ESPIRITO SANTO": "ES",
    "GOIAS": "GO",
    "MARANHAO": "MA",
    "MATO GROSSO": "MT",
    "MATO GROSSO DO SUL": "MS",
    "MINAS GERAIS": "MG",
    "PARA": "PA",
    "PARAIBA": "PB",
    "PARANA": "PR",
    "PERNAMBUCO": "PE",
    "PIAUI": "PI",
    "RIO DE JANEIRO": "RJ",
    "RIO GRANDE DO NORTE": "RN",
    "RIO GRANDE DO SUL": "RS",
    "RONDONIA": "RO",
    "RORAIMA": "RR",
    "SANTA CATARINA": "SC",
    "SAO PAULO": "SP",
    "SERGIPE": "SE",
    "TOCANTINS": "TO",
}

_DEFAULT_UFS_GEOJSON = PROJECT_ROOT / "dashboard" / "public" / "geo" / "ufs.geojson"

UPDATE_MUNICIPIO_BY_COD_SQL = """
    UPDATE serving.fact_emprego_municipio_mes
    SET uf = %s,
        municipio = %s,
        admissoes = %s,
        desligamentos = %s,
        saldo = %s,
        updated_at = NOW()
    WHERE ano = %s AND mes = %s AND cod_municipio = %s;
"""

INSERT_MUNICIPIO_SQL = """
    INSERT INTO serving.fact_emprego_municipio_mes
        (ano, mes, uf, municipio, cod_municipio, admissoes, desligamentos, saldo, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (ano, mes, uf, municipio) DO UPDATE SET
        cod_municipio = EXCLUDED.cod_municipio,
        admissoes = EXCLUDED.admissoes,
        desligamentos = EXCLUDED.desligamentos,
        saldo = EXCLUDED.saldo,
        updated_at = NOW();
"""

# Schema legado: coluna uf (sigla) é a chave natural.
# uf_nome/cod_uf são aditivos (migration 002); se ausentes, use SQL mínimo.
UPSERT_UF_SQL = """
    INSERT INTO serving.fact_emprego_uf_mes
        (ano, mes, uf, admissoes, desligamentos, saldo, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (ano, mes, uf) DO UPDATE SET
        admissoes = EXCLUDED.admissoes,
        desligamentos = EXCLUDED.desligamentos,
        saldo = EXCLUDED.saldo,
        updated_at = NOW();
"""

UPSERT_UF_RICH_SQL = """
    INSERT INTO serving.fact_emprego_uf_mes
        (ano, mes, uf, uf_nome, cod_uf, admissoes, desligamentos, saldo, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (ano, mes, uf) DO UPDATE SET
        uf_nome = EXCLUDED.uf_nome,
        cod_uf = EXCLUDED.cod_uf,
        admissoes = EXCLUDED.admissoes,
        desligamentos = EXCLUDED.desligamentos,
        saldo = EXCLUDED.saldo,
        updated_at = NOW();
"""

# Schema legado: PK (ano, mes, municipio); coluna ICTT quoted; cod_municipio aditivo.
UPDATE_ICTT_BY_COD_SQL = """
    UPDATE serving.fact_ictt_municipio_pr_mes
    SET uf = %s,
        municipio = %s,
        municipio_norm = %s,
        status_calculo = %s,
        "ICTT" = %s,
        ranking_ictt = %s,
        percentil_ictt = %s,
        classe_ictt = %s,
        admissoes = %s,
        desligamentos = %s,
        saldo = %s,
        updated_at = NOW()
    WHERE ano = %s AND mes = %s AND cod_municipio = %s;
"""

UPSERT_ICTT_BY_NAME_SQL = """
    INSERT INTO serving.fact_ictt_municipio_pr_mes
        (ano, mes, uf, municipio, municipio_norm, cod_municipio, status_calculo,
         "ICTT", ranking_ictt, percentil_ictt, classe_ictt,
         admissoes, desligamentos, saldo, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (ano, mes, municipio) DO UPDATE SET
        uf = EXCLUDED.uf,
        municipio_norm = EXCLUDED.municipio_norm,
        cod_municipio = EXCLUDED.cod_municipio,
        status_calculo = EXCLUDED.status_calculo,
        "ICTT" = EXCLUDED."ICTT",
        ranking_ictt = EXCLUDED.ranking_ictt,
        percentil_ictt = EXCLUDED.percentil_ictt,
        classe_ictt = EXCLUDED.classe_ictt,
        admissoes = EXCLUDED.admissoes,
        desligamentos = EXCLUDED.desligamentos,
        saldo = EXCLUDED.saldo,
        updated_at = NOW();
"""

DATASET_FILES: dict[str, str] = {
    "municipio-pr": "tabela_municipio_pr",
    "municipio-rmc": "tabela_municipio_rmc",
    "uf": "tabela_uf",
    "ictt-pr": "tabela_ictt_municipio_pr",
}


def normalize_key(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    text = PUNCT_RE.sub(" ", text)
    text = " ".join(text.lower().split())
    return text.upper() if text else None


def format_cod_municipio(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return None
    if text.endswith(".0") and text.replace(".", "", 1).isdigit():
        text = text[:-2]
    if text.isdigit() and len(text) < 7:
        text = text.zfill(7)
    return text


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def resolve_gold_paths(ano: int, mes: int, base_name: str) -> list[Path]:
    folder = GOLD_CAGED_DIR / f"ano={ano}" / f"mes={mes:02d}"
    paths: list[Path] = []
    parquet = folder / f"{base_name}.parquet"
    csv = folder / f"{base_name}.csv"
    if parquet.is_file():
        paths.append(parquet)
    if csv.is_file():
        paths.append(csv)
    return paths


def read_gold(ano: int, mes: int, base_name: str) -> tuple[pd.DataFrame, Path]:
    paths = resolve_gold_paths(ano, mes, base_name)
    if not paths:
        raise FileNotFoundError(
            f"Tabela Gold ausente: {base_name} em "
            f"{GOLD_CAGED_DIR / f'ano={ano}' / f'mes={mes:02d}'}"
        )
    parquet = next((p for p in paths if p.suffix.lower() == ".parquet"), None)
    path = parquet or paths[0]
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path), path
    return pd.read_csv(path), path


def resolve_uf_sigla(raw_uf: object) -> str | None:
    if raw_uf is None:
        return None
    text = str(raw_uf).strip()
    if not text or text.lower() == "nan":
        return None
    if len(text) == 2 and text.isalpha():
        return text.upper()
    key = normalize_key(text)
    if key and key in UF_SIGLA_BY_NORM:
        return UF_SIGLA_BY_NORM[key]
    return None


def load_uf_cod_lookup(geojson_path: Path | None = None) -> dict[str, str]:
    path = geojson_path or _DEFAULT_UFS_GEOJSON
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for feat in payload.get("features") or []:
        props = feat.get("properties") or {}
        sigla = props.get("uf_sigla")
        cod = props.get("cod_uf")
        if sigla is None or cod is None:
            continue
        s = str(sigla).strip().upper()
        c = str(cod).strip()
        if s and c:
            out[s] = c.zfill(2) if c.isdigit() else c
    return out


def _municipio_name_series(df: pd.DataFrame) -> pd.Series:
    if "municipio_norm" in df.columns:
        return df["municipio_norm"]
    if "municipio" in df.columns:
        return df["municipio"]
    raise ValueError(f"Coluna municipio ausente: {list(df.columns)}")


def _upsert_municipio_row(
    cur: Any,
    *,
    ano: int,
    mes: int,
    uf_sigla: str,
    municipio: str,
    cod: str,
    admissoes: int,
    desligamentos: int,
    saldo: int,
) -> None:
    """Idempotente por (ano, mes, cod_municipio); fallback na PK (ano,mes,uf,municipio)."""
    cur.execute(
        UPDATE_MUNICIPIO_BY_COD_SQL,
        (uf_sigla, municipio, admissoes, desligamentos, saldo, ano, mes, cod),
    )
    if cur.rowcount and cur.rowcount > 0:
        return
    cur.execute(
        INSERT_MUNICIPIO_SQL,
        (ano, mes, uf_sigla, municipio, cod, admissoes, desligamentos, saldo),
    )


def load_fact_municipio_dataset(
    *,
    dataset: str,
    ano: int,
    mes: int,
) -> dict[str, Any]:
    if dataset not in ("municipio-pr", "municipio-rmc"):
        raise ValueError(f"Dataset municipal inválido: {dataset}")

    base_name = DATASET_FILES[dataset]
    df, path = read_gold(ano, mes, base_name)
    required = ["uf", "municipio", "admissoes", "desligamentos", "saldo"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes em {path.name}: {missing}")

    if "cod_municipio" not in df.columns:
        raise ValueError(
            f"Dataset {dataset} exige coluna cod_municipio na Gold ({path.name}). "
            "Rode o enriquecimento: "
            "python scripts/enrich_gold_cod_municipio.py "
            f"--ano {ano} --mes {mes} --backup --strict"
        )

    rows_read = len(df)
    ignored_non_territorial = 0
    skipped_no_cod = 0
    upserted = 0
    names = _municipio_name_series(df)

    conn = get_connection()
    cur = conn.cursor()
    try:
        for idx, row in df.iterrows():
            key = normalize_key(
                names.loc[idx] if idx in names.index else row.get("municipio")
            )
            if key in SPECIAL_NON_MUNICIPIO:
                ignored_non_territorial += 1
                continue
            cod = format_cod_municipio(row.get("cod_municipio"))
            if cod is None:
                skipped_no_cod += 1
                continue
            uf_sigla = resolve_uf_sigla(row.get("uf")) or "PR"
            municipio = str(row.get("municipio") or "").strip()
            _upsert_municipio_row(
                cur,
                ano=int(ano),
                mes=int(mes),
                uf_sigla=uf_sigla,
                municipio=municipio,
                cod=cod,
                admissoes=_to_int(row.get("admissoes")) or 0,
                desligamentos=_to_int(row.get("desligamentos")) or 0,
                saldo=_to_int(row.get("saldo")) or 0,
            )
            upserted += 1

        if skipped_no_cod > 0:
            raise ValueError(
                f"Dataset {dataset}: {skipped_no_cod} município(s) real(is) sem "
                "cod_municipio. Não há fallback por nome na carga principal."
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    report = {
        "dataset": dataset,
        "file": str(path),
        "rows_read": rows_read,
        "rows_loadable": upserted,
        "ignored_non_territorial": ignored_non_territorial,
        "skipped_no_cod": skipped_no_cod,
        "upserted": upserted,
        "ano": ano,
        "mes": mes,
    }
    _print_report(report)
    return report


def load_fact_uf(*, ano: int, mes: int) -> dict[str, Any]:
    base_name = DATASET_FILES["uf"]
    df, path = read_gold(ano, mes, base_name)
    required = ["uf", "admissoes", "desligamentos", "saldo"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes em {path.name}: {missing}")

    uf_cod = load_uf_cod_lookup()
    rows_read = len(df)
    skipped = 0
    upserted = 0
    use_rich = True

    conn = get_connection()
    cur = conn.cursor()
    try:
        for _, row in df.iterrows():
            raw_uf = row.get("uf")
            sigla = resolve_uf_sigla(raw_uf)
            if sigla is None:
                skipped += 1
                continue
            nome = str(raw_uf).strip() if raw_uf is not None else sigla
            adm = _to_int(row.get("admissoes")) or 0
            des = _to_int(row.get("desligamentos")) or 0
            saldo = _to_int(row.get("saldo")) or 0
            try:
                if use_rich:
                    cur.execute(
                        UPSERT_UF_RICH_SQL,
                        (int(ano), int(mes), sigla, nome, uf_cod.get(sigla), adm, des, saldo),
                    )
                else:
                    cur.execute(
                        UPSERT_UF_SQL,
                        (int(ano), int(mes), sigla, adm, des, saldo),
                    )
            except Exception as exc:
                if use_rich and "uf_nome" in str(exc):
                    conn.rollback()
                    use_rich = False
                    cur.execute(
                        UPSERT_UF_SQL,
                        (int(ano), int(mes), sigla, adm, des, saldo),
                    )
                else:
                    raise
            upserted += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    report = {
        "dataset": "uf",
        "file": str(path),
        "rows_read": rows_read,
        "rows_loadable": upserted,
        "ignored_non_territorial": 0,
        "skipped_no_cod": skipped,
        "upserted": upserted,
        "ano": ano,
        "mes": mes,
    }
    _print_report(report)
    return report


def load_fact_ictt_pr(*, ano: int, mes: int) -> dict[str, Any]:
    base_name = DATASET_FILES["ictt-pr"]
    df, path = read_gold(ano, mes, base_name)
    if "cod_municipio" not in df.columns:
        raise ValueError(
            f"Dataset ictt-pr exige coluna cod_municipio na Gold ({path.name}). "
            "Rode o enriquecimento antes da carga PostGIS."
        )

    rows_read = len(df)
    ignored_non_territorial = 0
    skipped_no_cod = 0
    upserted = 0
    names = _municipio_name_series(df)

    conn = get_connection()
    cur = conn.cursor()
    try:
        for idx, row in df.iterrows():
            key = normalize_key(
                names.loc[idx] if idx in names.index else row.get("municipio")
            )
            if key in SPECIAL_NON_MUNICIPIO:
                ignored_non_territorial += 1
                continue
            cod = format_cod_municipio(row.get("cod_municipio"))
            if cod is None:
                skipped_no_cod += 1
                continue
            uf_sigla = resolve_uf_sigla(row.get("uf")) or "PR"
            municipio = str(row.get("municipio") or "").strip() or cod
            municipio_norm = str(row.get("municipio_norm") or "").strip() or key
            status = str(row.get("status_calculo") or "").strip() or None
            ictt = _to_float(row.get("ICTT"))
            ranking = _to_float(row.get("ranking_ictt"))
            percentil = _to_float(row.get("percentil_ictt"))
            classe = str(row.get("classe_ictt") or "").strip() or None
            adm = _to_int(row.get("admissoes"))
            des = _to_int(row.get("desligamentos"))
            saldo = _to_int(row.get("saldo"))
            cur.execute(
                UPDATE_ICTT_BY_COD_SQL,
                (
                    uf_sigla,
                    municipio,
                    municipio_norm,
                    status,
                    ictt,
                    ranking,
                    percentil,
                    classe,
                    adm,
                    des,
                    saldo,
                    int(ano),
                    int(mes),
                    cod,
                ),
            )
            if not cur.rowcount:
                cur.execute(
                    UPSERT_ICTT_BY_NAME_SQL,
                    (
                        int(ano),
                        int(mes),
                        uf_sigla,
                        municipio,
                        municipio_norm,
                        cod,
                        status,
                        ictt,
                        ranking,
                        percentil,
                        classe,
                        adm,
                        des,
                        saldo,
                    ),
                )
            upserted += 1
        if skipped_no_cod > 0:
            raise ValueError(
                f"Dataset ictt-pr: {skipped_no_cod} município(s) real(is) sem "
                "cod_municipio. Não há fallback por nome."
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    report = {
        "dataset": "ictt-pr",
        "file": str(path),
        "rows_read": rows_read,
        "rows_loadable": upserted,
        "ignored_non_territorial": ignored_non_territorial,
        "skipped_no_cod": skipped_no_cod,
        "upserted": upserted,
        "ano": ano,
        "mes": mes,
    }
    _print_report(report)
    return report


def _print_report(report: dict[str, Any]) -> None:
    print(f"--- load_fact_tables [{report['dataset']}] ---")
    print(f"  file={report['file']}")
    print(f"  competencia={report['ano']}-{report['mes']:02d}")
    print(f"  rows_read={report['rows_read']}")
    print(f"  rows_loadable={report['rows_loadable']}")
    print(f"  ignored_non_territorial={report['ignored_non_territorial']}")
    print(f"  skipped_no_cod_or_uf={report['skipped_no_cod']}")
    print(f"  upserted={report['upserted']}")
    print("")
    logger.info(
        "[LOAD] dataset=%s competencia=%s-%02d read=%s upserted=%s ignored=%s skipped=%s",
        report["dataset"],
        report["ano"],
        report["mes"],
        report["rows_read"],
        report["upserted"],
        report["ignored_non_territorial"],
        report["skipped_no_cod"],
    )


def load_fact_emprego_municipio(ano: int = DEFAULT_ANO, mes: int = DEFAULT_MES):
    """Compatibilidade com routes_admin: carrega municipio-pr (exige cod_municipio)."""
    return load_fact_municipio_dataset(dataset="municipio-pr", ano=ano, mes=mes)


def load_dataset(dataset: str, *, ano: int, mes: int) -> dict[str, Any]:
    if dataset in ("municipio-pr", "municipio-rmc"):
        return load_fact_municipio_dataset(dataset=dataset, ano=ano, mes=mes)
    if dataset == "uf":
        return load_fact_uf(ano=ano, mes=mes)
    if dataset == "ictt-pr":
        return load_fact_ictt_pr(ano=ano, mes=mes)
    raise ValueError(
        f"Dataset desconhecido: {dataset}. Use: {', '.join(sorted(DATASET_FILES))}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga idempotente Gold → PostGIS (fatos)."
    )
    parser.add_argument(
        "--dataset",
        required=True,
        choices=sorted(DATASET_FILES.keys()),
        help="municipio-pr | municipio-rmc | uf | ictt-pr",
    )
    parser.add_argument("--ano", type=int, default=DEFAULT_ANO)
    parser.add_argument("--mes", type=int, default=DEFAULT_MES)
    args = parser.parse_args(argv)
    try:
        load_dataset(args.dataset, ano=args.ano, mes=args.mes)
    except Exception as exc:
        print(f"ERRO: {exc}")
        logger.exception("[LOAD] falha dataset=%s", args.dataset)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
