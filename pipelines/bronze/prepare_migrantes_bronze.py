"""Prepara microdados Bronze mensais a partir da base filtrada de migrantes (RAIS/CAGED).

Converte o CSV original do Ministério do Trabalho para o formato esperado pelo
pipeline existente (``microdados.txt``, separador ``;``, UTF-8), sem alterar
Silver, Gold, API ou dashboard.

Uso típico (piloto, uma competência por vez)::

    python -m pipelines.bronze.prepare_migrantes_bronze --ano 2026 --mes 1
    python -m pipelines.bronze.prepare_migrantes_bronze --ano 2026 --mes 1 --dry-run

Após gerar o Bronze, valide apenas a camada Bronze com o job existente::

    python -m pipelines.jobs.run_monthly_pipeline --ano 2026 --mes 1 --validate-bronze-only

Convenção de armazenamento (Opção B do scan de compatibilidade):
- Original imutável: ``data-lake/raw/migrantes/ano=YYYY/RAIS_CTPS_CAGED_YYYY_MOV.csv``
- Bronze gerado: ``data-lake/bronze/caged/ano=YYYY/mes=MM/microdados.txt``
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.core.config import BRONZE_CAGED_DIR, DATA_LAKE_DIR, PIPELINE_LOG_FILE
from app.core.logging import setup_logger
from pipelines.bronze.microdados_contract import EXPECTED_ENCODING, EXPECTED_SEPARATOR
from pipelines.common.utils import ensure_dir, save_json
from pipelines.silver.clean_caged import classificar_faixa_etaria

logger = setup_logger("bronze.prepare_migrantes", PIPELINE_LOG_FILE)

RAW_MIGRANTES_DIR = DATA_LAKE_DIR / "raw" / "migrantes"
METADATA_FILENAME = "migrantes_prep_metadata.json"

# Mapeamentos de colunas (base migrante → contrato Bronze/Silver atual).
COLUMN_RENAMES: dict[str, str] = {
    "nivel_instrucao": "graudeinstrucao",
    "faixa_horas_contrat": "horascontratuais",
}

# Idades representativas alinhadas a ``classificar_faixa_etaria`` em clean_caged.py.
# "01"→17→"Até 17 anos"; "02"→21→"18 a 24 anos"; …; "07"→65→"65 anos ou mais".
FAIXA_ETARIA_TO_IDADE: dict[str, int] = {
    "01": 17,
    "02": 21,
    "03": 29,
    "04": 39,
    "05": 49,
    "06": 59,
    "07": 65,
}

# Códigos conhecidos sem idade representativa (Silver classifica como "Ignorado").
FAIXA_ETARIA_SEM_IDADE: frozenset[str] = frozenset({"0NA"})

# Colunas mínimas exigidas na base preparada (pós-mapeamento/derivação).
PREPARED_REQUIRED_COLUMNS: tuple[str, ...] = (
    "competenciamov",
    "saldomovimentacao",
    "horascontratuais",
    "salario",
    "valorsalariofixo",
    "graudeinstrucao",
    "idade",
    "uf",
    "municipio",
    "secao",
    "cbo2002ocupacao",
    "sexo",
    "faixa_etaria",
    "tipomovimentacao",
)

APPLIED_MAPPINGS: list[dict[str, str]] = [
    {"source": "nivel_instrucao", "target": "graudeinstrucao", "type": "rename"},
    {"source": "faixa_horas_contrat", "target": "horascontratuais", "type": "rename"},
    {"source": "faixa_etaria", "target": "idade", "type": "derive"},
]


class PrepareMigrantesError(Exception):
    """Falha na preparação da base migrante para Bronze."""


def raw_migrantes_path(ano: int) -> Path:
    return RAW_MIGRANTES_DIR / f"ano={ano}" / f"RAIS_CTPS_CAGED_{ano}_MOV.csv"


def bronze_mes_dir(ano: int, mes: int) -> Path:
    return BRONZE_CAGED_DIR / f"ano={ano}" / f"mes={mes:02d}"


def expected_competenciamov(ano: int, mes: int) -> str:
    return f"{ano}{mes:02d}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_faixa_code(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().strip('"')
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    if text.isdigit():
        return text.zfill(2)
    return text


def derive_idade_from_faixa_etaria(faixa_series: pd.Series) -> pd.Series:
    """Deriva ``idade`` numérica a partir dos códigos de ``faixa_etaria``."""
    codes = faixa_series.map(_normalize_faixa_code)

    def _lookup(code: str | None):
        if code is None:
            return pd.NA
        if code in FAIXA_ETARIA_SEM_IDADE:
            return pd.NA
        if code in FAIXA_ETARIA_TO_IDADE:
            return FAIXA_ETARIA_TO_IDADE[code]
        return pd.NA  # sentinel for unknown detection

    idades = codes.map(_lookup)
    unknown_mask = codes.notna() & ~codes.isin(FAIXA_ETARIA_SEM_IDADE) & ~codes.isin(
        FAIXA_ETARIA_TO_IDADE.keys()
    )
    if unknown_mask.any():
        sample = sorted(codes[unknown_mask].dropna().unique().tolist())[:10]
        raise PrepareMigrantesError(
            "Códigos de faixa_etaria não mapeados para idade: "
            + ", ".join(sample)
        )
    return idades


def rename_migrante_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica renomeações mínimas exigidas pelo contrato Bronze/Silver."""
    missing_sources = [src for src in COLUMN_RENAMES if src not in df.columns]
    if missing_sources:
        raise PrepareMigrantesError(
            "Colunas de origem ausentes para renomeação: "
            + ", ".join(missing_sources)
        )
    return df.rename(columns=COLUMN_RENAMES)


def filter_by_competencia(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    """Filtra linhas cuja competenciamov corresponde a ano/mês."""
    if "competenciamov" not in df.columns:
        raise PrepareMigrantesError("Coluna 'competenciamov' ausente na base de entrada.")

    expected = expected_competenciamov(ano, mes)
    competencia = (
        df["competenciamov"]
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    return df.loc[competencia == expected].copy()


def validate_prepared_columns(df: pd.DataFrame) -> None:
    """Garante presença das colunas mínimas antes de gravar Bronze."""
    missing = [col for col in PREPARED_REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise PrepareMigrantesError(
            "Colunas obrigatórias ausentes na base preparada: " + ", ".join(missing)
        )


def prepare_migrantes_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica renomeações, deriva ``idade`` e valida colunas mínimas."""
    prepared = rename_migrante_columns(df)
    if "faixa_etaria" not in prepared.columns:
        raise PrepareMigrantesError("Coluna 'faixa_etaria' ausente na base de entrada.")
    prepared["idade"] = derive_idade_from_faixa_etaria(prepared["faixa_etaria"])
    validate_prepared_columns(prepared)
    return prepared


def read_migrantes_csv(source_path: Path) -> pd.DataFrame:
    if not source_path.is_file():
        raise PrepareMigrantesError(
            f"Arquivo original não encontrado: {source_path}. "
            "Coloque o CSV em data-lake/raw/migrantes/ano=YYYY/ sem alterá-lo."
        )
    return pd.read_csv(
        source_path,
        sep=";",
        encoding="utf-8",
        low_memory=False,
    )


def build_metadata(
    *,
    source_path: Path,
    ano: int,
    mes: int,
    competencia: str,
    rows_read: int,
    rows_filtered: int,
    rows_saved: int,
    source_sha256: str,
    columns: list[str],
    dry_run: bool,
) -> dict:
    return {
        "fonte": "RAIS_CTPS_CAGED_migrantes_filtrados",
        "descricao": (
            "Bronze gerado a partir de base de migrantes já filtrada "
            "(Ministério do Trabalho); não é microdados nacional completo do Novo CAGED."
        ),
        "arquivo_original_nome": source_path.name,
        "arquivo_original_caminho": source_path.as_posix(),
        "ano": ano,
        "mes": mes,
        "competencia_filtrada": competencia,
        "linhas_lidas": rows_read,
        "linhas_filtradas": rows_filtered,
        "linhas_salvas": rows_saved,
        "mapeamentos_aplicados": APPLIED_MAPPINGS,
        "sha256_arquivo_original": source_sha256,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "colunas_geradas": columns,
        "separador": EXPECTED_SEPARATOR,
        "encoding": EXPECTED_ENCODING,
    }


def print_dry_run_summary(
    *,
    ano: int,
    mes: int,
    competencia: str,
    rows_read: int,
    rows_filtered: int,
    prepared: pd.DataFrame,
    source_path: Path,
    output_path: Path,
) -> None:
    idade_sample = prepared["idade"].head(3).tolist()
    faixa_sample = prepared["faixa_etaria"].head(3).tolist()
    faixas_derivadas = [
        classificar_faixa_etaria(v) for v in prepared["idade"].dropna().head(5)
    ]

    print("=== prepare_migrantes_bronze (dry-run) ===")
    print(f"Arquivo original: {source_path}")
    print(f"Competência alvo: {competencia} (ano={ano}, mes={mes:02d})")
    print(f"Linhas lidas: {rows_read}")
    print(f"Linhas filtradas: {rows_filtered}")
    print(f"Saída prevista: {output_path}")
    print(f"Colunas ({len(prepared.columns)}): {', '.join(prepared.columns.tolist())}")
    print(f"Amostra faixa_etaria -> idade: {list(zip(faixa_sample, idade_sample))}")
    print(f"Faixas derivadas (amostra via classificar_faixa_etaria): {faixas_derivadas}")
    missing = [c for c in PREPARED_REQUIRED_COLUMNS if c not in prepared.columns]
    print(f"Colunas obrigatórias faltantes: {missing or 'nenhuma'}")


def run_prepare_migrantes_bronze(
    ano: int,
    mes: int,
    *,
    dry_run: bool = False,
    source_path: Path | None = None,
) -> dict:
    """Lê CSV migrante, prepara e grava Bronze mensal (ou apenas simula com dry_run)."""
    source = source_path or raw_migrantes_path(ano)
    competencia = expected_competenciamov(ano, mes)
    bronze_dir = bronze_mes_dir(ano, mes)
    output_path = bronze_dir / "microdados.txt"
    metadata_path = bronze_dir / METADATA_FILENAME

    logger.info(
        "[PREP-MIG] Iniciando | ano=%s mes=%s competencia=%s dry_run=%s",
        ano,
        mes,
        competencia,
        dry_run,
    )

    source_sha256 = sha256_file(source)
    df_raw = read_migrantes_csv(source)
    rows_read = len(df_raw)

    df_filtered = filter_by_competencia(df_raw, ano, mes)
    rows_filtered = len(df_filtered)
    if rows_filtered == 0:
        raise PrepareMigrantesError(
            f"Nenhuma linha com competenciamov={competencia} em {source.name}."
        )

    prepared = prepare_migrantes_dataframe(df_filtered)

    if dry_run:
        print_dry_run_summary(
            ano=ano,
            mes=mes,
            competencia=competencia,
            rows_read=rows_read,
            rows_filtered=rows_filtered,
            prepared=prepared,
            source_path=source,
            output_path=output_path,
        )
        metadata = build_metadata(
            source_path=source,
            ano=ano,
            mes=mes,
            competencia=competencia,
            rows_read=rows_read,
            rows_filtered=rows_filtered,
            rows_saved=0,
            source_sha256=source_sha256,
            columns=prepared.columns.tolist(),
            dry_run=True,
        )
        logger.info("[PREP-MIG] Dry-run concluído | linhas_filtradas=%s", rows_filtered)
        return metadata

    ensure_dir(bronze_dir)
    prepared.to_csv(
        output_path,
        sep=EXPECTED_SEPARATOR,
        encoding=EXPECTED_ENCODING,
        index=False,
    )

    metadata = build_metadata(
        source_path=source,
        ano=ano,
        mes=mes,
        competencia=competencia,
        rows_read=rows_read,
        rows_filtered=rows_filtered,
        rows_saved=len(prepared),
        source_sha256=source_sha256,
        columns=prepared.columns.tolist(),
        dry_run=False,
    )
    save_json(metadata, metadata_path)

    logger.info(
        "[PREP-MIG] Bronze gravado | path=%s linhas=%s metadata=%s",
        output_path,
        len(prepared),
        metadata_path,
    )
    return metadata


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepara microdados Bronze mensais a partir da base filtrada de migrantes."
        ),
    )
    parser.add_argument("--ano", type=int, required=True, help="Ano da competência (ex.: 2026)")
    parser.add_argument("--mes", type=int, required=True, help="Mês da competência (1-12)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula preparação sem gravar microdados.txt nem metadata JSON",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if not (1 <= args.mes <= 12):
        raise SystemExit("--mes deve estar entre 1 e 12.")

    try:
        run_prepare_migrantes_bronze(args.ano, args.mes, dry_run=args.dry_run)
    except PrepareMigrantesError as exc:
        logger.error("[PREP-MIG] %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
