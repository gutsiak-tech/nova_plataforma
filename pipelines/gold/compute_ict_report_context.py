"""
Contexto analítico determinístico do ICT (Índice de Competitividade do Trabalho).

Lê a tabela Gold ICTT existente e gera JSON estruturado para uso futuro em relatórios.
Não utiliza IA, APIs externas nem recálculo do índice.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from app.core.config import DATA_LAKE_DIR, PIPELINE_LOG_FILE
from app.core.logging import setup_logger
from pipelines.common.utils import ensure_dir, save_json
from pipelines.gold.aggregate_indicators import gold_mes_dir
from pipelines.gold.compute_ictt import CLASSE_ICTT_SEM_DADOS, SCOPE_OUTPUT_STEM

logger = setup_logger("gold.ict_report_context", PIPELINE_LOG_FILE)

Scope = Literal["pr"]
SUPPORTED_SCOPES: frozenset[str] = frozenset({"pr"})
SCOPE_UNSUPPORTED_MSG = (
    "O contexto analítico do ICT está disponível inicialmente apenas para o escopo Paraná."
)

ICTT_TABLE_COLUMN = "ICTT"
DIMENSION_COLUMNS: tuple[str, ...] = (
    "dim_dinamismo",
    "dim_remuneracao",
    "dim_qualidade_emprego",
    "dim_perfil_trabalhador",
    "dim_complexidade",
)

INTERPRETATION_NOTES: tuple[str, ...] = (
    "O ICT é um índice relativo entre municípios com dados suficientes na competência selecionada.",
    "Municípios sem ICT não devem ser interpretados como municípios de baixo desempenho.",
    "Municípios em cinza não tiveram movimentação formal migratória suficiente para cálculo.",
    "O ICT não mede causalidade e não substitui análise qualitativa local.",
    "Nesta fase, o relatório não utiliza Moran, LISA ou autocorrelação espacial.",
)

COMPETENCIA_DIR_RE = re.compile(r"^ano=(\d{4})$")
COMPETENCIA_MES_RE = re.compile(r"^mes=(\d{2})$")


def finite_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(num):
        return None
    return num


def round_or_none(value: Any, digits: int = 2) -> float | None:
    num = finite_number(value)
    if num is None:
        return None
    return round(num, digits)


def dataframe_to_json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: dataframe_to_json_safe(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [dataframe_to_json_safe(item) for item in obj]
    if isinstance(obj, tuple):
        return [dataframe_to_json_safe(item) for item in obj]
    if obj is None:
        return None
    if isinstance(obj, (np.floating, float)):
        num = float(obj)
        return None if not math.isfinite(num) else round(num, 2)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, str):
        return obj
    if pd.isna(obj):
        return None
    num = finite_number(obj)
    if num is not None:
        return round(num, 2)
    return obj


def report_context_dir(ano: int, mes: int) -> Path:
    return DATA_LAKE_DIR / "gold" / "reports" / "ict" / f"ano={ano}" / f"mes={mes:02d}"


def ictt_parquet_path(ano: int, mes: int, scope: str) -> Path:
    stem = SCOPE_OUTPUT_STEM[scope]  # type: ignore[index]
    return gold_mes_dir(ano, mes) / f"{stem}.parquet"


def read_ictt_table(ano: int, mes: int, scope: str) -> pd.DataFrame:
    if scope not in SUPPORTED_SCOPES:
        raise ValueError(SCOPE_UNSUPPORTED_MSG)

    path = ictt_parquet_path(ano, mes, scope)
    if not path.is_file():
        raise FileNotFoundError(f"Tabela ICTT não encontrada: {path}")
    return pd.read_parquet(path)


def _competencia_key(ano: int, mes: int) -> tuple[int, int]:
    return ano, mes


def list_available_ictt_months(scope: str, ano_max: int, mes_max: int) -> list[tuple[int, int]]:
    if scope not in SUPPORTED_SCOPES:
        raise ValueError(SCOPE_UNSUPPORTED_MSG)

    gold_root = DATA_LAKE_DIR / "gold" / "caged"
    if not gold_root.is_dir():
        return []

    target = _competencia_key(ano_max, mes_max)
    months: list[tuple[int, int]] = []

    for ano_dir in gold_root.iterdir():
        if not ano_dir.is_dir():
            continue
        ano_match = COMPETENCIA_DIR_RE.match(ano_dir.name)
        if not ano_match:
            continue
        ano = int(ano_match.group(1))

        for mes_dir in ano_dir.iterdir():
            if not mes_dir.is_dir():
                continue
            mes_match = COMPETENCIA_MES_RE.match(mes_dir.name)
            if not mes_match:
                continue
            mes = int(mes_match.group(1))
            key = _competencia_key(ano, mes)
            if key > target:
                continue
            if ictt_parquet_path(ano, mes, scope).is_file():
                months.append(key)

    months.sort()
    return months


def valid_ict_mask(df: pd.DataFrame) -> pd.Series:
    return df[ICTT_TABLE_COLUMN].map(finite_number).notna()


def valid_ict_df(df: pd.DataFrame) -> pd.DataFrame:
    mask = valid_ict_mask(df)
    return df.loc[mask].copy()


def compute_summary(df: pd.DataFrame) -> dict[str, Any]:
    valid = valid_ict_df(df)
    municipios_total = int(len(df))
    municipios_com_ict = int(len(valid))
    municipios_sem_base = municipios_total - municipios_com_ict
    percentual_com_ict = (
        round((municipios_com_ict / municipios_total) * 100, 2) if municipios_total else None
    )

    ict_values = valid[ICTT_TABLE_COLUMN].map(finite_number).dropna()
    ict_medio = round_or_none(ict_values.mean()) if not ict_values.empty else None
    ict_mediano = round_or_none(ict_values.median()) if not ict_values.empty else None
    ict_minimo = round_or_none(ict_values.min()) if not ict_values.empty else None
    ict_maximo = round_or_none(ict_values.max()) if not ict_values.empty else None

    municipio_lider: str | None = None
    ranking_lider: int | None = None
    if not valid.empty:
        leader = valid.nsmallest(1, "ranking_ictt").iloc[0]
        municipio_lider = str(leader["municipio"])
        ranking_lider = int(finite_number(leader["ranking_ictt"]) or 0)

    return {
        "municipios_total": municipios_total,
        "municipios_com_ict": municipios_com_ict,
        "municipios_sem_base": municipios_sem_base,
        "percentual_com_ict": percentual_com_ict,
        "ict_medio": ict_medio,
        "ict_mediano": ict_mediano,
        "ict_minimo": ict_minimo,
        "ict_maximo": ict_maximo,
        "municipio_lider": municipio_lider,
        "ranking_lider": ranking_lider,
    }


def compute_class_distribution(df: pd.DataFrame) -> dict[str, int]:
    counts = df["classe_ictt"].fillna(CLASSE_ICTT_SEM_DADOS).value_counts()
    return {str(label): int(count) for label, count in counts.items()}


def _row_to_rank_entry(row: pd.Series) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "ranking": int(finite_number(row["ranking_ictt"]) or 0),
        "municipio": str(row["municipio"]),
        "ict": round_or_none(row[ICTT_TABLE_COLUMN]),
        "classe": str(row.get("classe_ictt") or ""),
    }
    for field in ("admissoes", "desligamentos", "saldo"):
        value = finite_number(row.get(field))
        entry[field] = int(value) if value is not None else None
    for field in DIMENSION_COLUMNS:
        entry[field] = round_or_none(row.get(field))
    return entry


def compute_top_bottom(df: pd.DataFrame, limit: int = 10) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    valid = valid_ict_df(df)
    if valid.empty:
        return [], []

    ordered = valid.sort_values("ranking_ictt", ascending=True, kind="mergesort")
    top = [_row_to_rank_entry(row) for _, row in ordered.head(limit).iterrows()]
    bottom = [_row_to_rank_entry(row) for _, row in ordered.tail(limit).iloc[::-1].iterrows()]
    return top, bottom


def _monthly_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    valid = valid_ict_df(df)
    summary = compute_summary(df)
    ict_values = valid[ICTT_TABLE_COLUMN].map(finite_number).dropna()

    competencia = str(df["competencia_str"].iloc[0]) if "competencia_str" in df.columns and len(df) else None
    if not competencia:
        ano = int(df["ano"].iloc[0])
        mes = int(df["mes"].iloc[0])
        competencia = f"{ano}-{mes:02d}"

    return {
        "competencia_str": competencia,
        "municipios_com_ict": summary["municipios_com_ict"],
        "municipios_sem_base": summary["municipios_sem_base"],
        "ict_medio": summary["ict_medio"],
        "ict_mediano": round_or_none(ict_values.median()) if not ict_values.empty else None,
        "ict_maximo": summary["ict_maximo"],
        "municipio_lider": summary["municipio_lider"],
        "admissoes_total": int(valid["admissoes"].fillna(0).sum()) if not valid.empty else 0,
        "desligamentos_total": int(valid["desligamentos"].fillna(0).sum()) if not valid.empty else 0,
        "saldo_total": int(valid["saldo"].fillna(0).sum()) if not valid.empty else 0,
    }


def compute_monthly_evolution(scope: str, ano: int, mes: int) -> list[dict[str, Any]]:
    months = list_available_ictt_months(scope, ano, mes)
    evolution: list[dict[str, Any]] = []
    for ano_ref, mes_ref in months:
        df = read_ictt_table(ano_ref, mes_ref, scope)
        evolution.append(_monthly_snapshot(df))
    return evolution


def _dimension_extremes(valid: pd.DataFrame, column: str) -> dict[str, Any]:
    series = valid[column].map(finite_number)
    valid_rows = valid.loc[series.notna()].copy()
    if valid_rows.empty:
        return {
            "media": None,
            "mediana": None,
            "minimo": None,
            "maximo": None,
            "municipio_maior": None,
            "valor_maior": None,
            "municipio_menor": None,
            "valor_menor": None,
        }

    values = valid_rows[column].map(finite_number)
    max_idx = values.idxmax()
    min_idx = values.idxmin()
    max_row = valid_rows.loc[max_idx]
    min_row = valid_rows.loc[min_idx]

    return {
        "media": round_or_none(values.mean()),
        "mediana": round_or_none(values.median()),
        "minimo": round_or_none(values.min()),
        "maximo": round_or_none(values.max()),
        "municipio_maior": str(max_row["municipio"]),
        "valor_maior": round_or_none(max_row[column]),
        "municipio_menor": str(min_row["municipio"]),
        "valor_menor": round_or_none(min_row[column]),
    }


def compute_dimension_summary(df: pd.DataFrame) -> dict[str, dict[str, Any]]:
    valid = valid_ict_df(df)
    return {column: _dimension_extremes(valid, column) for column in DIMENSION_COLUMNS}


def _flag_entry(
    row: pd.Series,
    dimension: str,
    description: str,
) -> dict[str, Any]:
    return {
        "municipio": str(row["municipio"]),
        "ict": round_or_none(row[ICTT_TABLE_COLUMN]),
        "ranking_ictt": int(finite_number(row["ranking_ictt"]) or 0),
        dimension: round_or_none(row.get(dimension)),
        "descricao": description,
    }


def compute_diagnostic_flags(df: pd.DataFrame) -> dict[str, Any]:
    valid = valid_ict_df(df)
    summary = compute_summary(df)
    top20 = valid.sort_values("ranking_ictt", ascending=True, kind="mergesort").head(20)

    leaders_with_negative_quality: list[dict[str, Any]] = []
    for _, row in top20.iterrows():
        quality = finite_number(row.get("dim_qualidade_emprego"))
        if quality is not None and quality < 0:
            leaders_with_negative_quality.append(
                _flag_entry(
                    row,
                    "dim_qualidade_emprego",
                    "Município bem posicionado no ICT, mas com dimensão de qualidade do emprego abaixo da média dos municípios calculáveis.",
                )
            )

    leaders_with_negative_remuneration: list[dict[str, Any]] = []
    for _, row in top20.iterrows():
        remuneration = finite_number(row.get("dim_remuneracao"))
        if remuneration is not None and remuneration < 0:
            leaders_with_negative_remuneration.append(
                _flag_entry(
                    row,
                    "dim_remuneracao",
                    "Município bem posicionado no ICT, mas com dimensão de remuneração abaixo da média dos municípios calculáveis.",
                )
            )

    dynamism_p75 = valid["dim_dinamismo"].map(finite_number).quantile(0.75)
    complexity_p75 = valid["dim_complexidade"].map(finite_number).quantile(0.75)

    high_dynamism_low_quality: list[dict[str, Any]] = []
    for _, row in valid.iterrows():
        dynamism = finite_number(row.get("dim_dinamismo"))
        quality = finite_number(row.get("dim_qualidade_emprego"))
        if (
            dynamism is not None
            and quality is not None
            and dynamism > dynamism_p75
            and quality < 0
        ):
            high_dynamism_low_quality.append(
                _flag_entry(
                    row,
                    "dim_dinamismo",
                    "Município com dinamismo migratório elevado, porém qualidade do emprego abaixo de zero na escala relativa.",
                )
            )

    high_complexity_low_remuneration: list[dict[str, Any]] = []
    for _, row in valid.iterrows():
        complexity = finite_number(row.get("dim_complexidade"))
        remuneration = finite_number(row.get("dim_remuneracao"))
        if (
            complexity is not None
            and remuneration is not None
            and complexity > complexity_p75
            and remuneration < 0
        ):
            high_complexity_low_remuneration.append(
                _flag_entry(
                    row,
                    "dim_complexidade",
                    "Município com alta complexidade ocupacional, porém remuneração relativa abaixo de zero.",
                )
            )

    return {
        "leaders_with_negative_quality": leaders_with_negative_quality,
        "leaders_with_negative_remuneration": leaders_with_negative_remuneration,
        "high_dynamism_low_quality": high_dynamism_low_quality,
        "high_complexity_low_remuneration": high_complexity_low_remuneration,
        "municipios_sem_base": summary["municipios_sem_base"],
    }


def build_report_context(
    ano: int,
    mes: int,
    scope: str,
    *,
    ictt_df: pd.DataFrame | None = None,
    monthly_evolution: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Monta o contexto analítico.

    Por padrão lê Gold filesystem. Callers PostGIS podem passar ``ictt_df`` e
    ``monthly_evolution`` já carregados (mesmo contrato JSON).
    """
    scope_key = scope.lower().strip()
    if scope_key not in SUPPORTED_SCOPES:
        raise ValueError(SCOPE_UNSUPPORTED_MSG)

    df = ictt_df if ictt_df is not None else read_ictt_table(ano, mes, scope_key)
    if df is None or len(df) == 0:
        raise FileNotFoundError(
            f"Tabela ICTT vazia/indisponível para {scope_key} em {ano}-{mes:02d}."
        )

    competencia_str = (
        str(df["competencia_str"].iloc[0])
        if "competencia_str" in df.columns and len(df)
        else f"{ano}-{mes:02d}"
    )

    top_10, bottom_10 = compute_top_bottom(df, limit=10)
    evolution = (
        monthly_evolution
        if monthly_evolution is not None
        else compute_monthly_evolution(scope_key, ano, mes)
    )

    context = {
        "metadata": {
            "indicator": "ICT",
            "indicator_full_name": "Índice de Competitividade do Trabalho",
            "scope": scope_key,
            "ano": ano,
            "mes": mes,
            "competencia_str": competencia_str,
            "generated_from": SCOPE_OUTPUT_STEM[scope_key],  # type: ignore[index]
            "method_note": (
                "Contexto analítico determinístico gerado a partir da camada Gold. "
                "Não utiliza IA."
            ),
        },
        "summary": compute_summary(df),
        "class_distribution": compute_class_distribution(df),
        "top_10": top_10,
        "bottom_10": bottom_10,
        "monthly_evolution": evolution,
        "dimension_summary": compute_dimension_summary(df),
        "diagnostic_flags": compute_diagnostic_flags(df),
        "interpretation_notes": list(INTERPRETATION_NOTES),
    }
    return dataframe_to_json_safe(context)


def render_report_context_markdown(context: dict[str, Any]) -> str:
    meta = context["metadata"]
    summary = context["summary"]
    lines = [
        f"# Contexto analítico do ICT — {meta['competencia_str']} ({meta['scope'].upper()})",
        "",
        meta["method_note"],
        "",
        "## Resumo",
        f"- Municípios totais: {summary['municipios_total']}",
        f"- Municípios com ICT: {summary['municipios_com_ict']}",
        f"- Sem base suficiente: {summary['municipios_sem_base']}",
        f"- ICT médio: {summary['ict_medio']}",
        f"- ICT mediano: {summary['ict_mediano']}",
        f"- ICT máximo: {summary['ict_maximo']} ({summary['municipio_lider']})",
        "",
        "## Distribuição por classe",
    ]
    for label, count in context["class_distribution"].items():
        lines.append(f"- {label}: {count}")

    lines.extend(["", "## Top 10"])
    for item in context["top_10"]:
        lines.append(
            f"- {item['ranking']}. {item['municipio']} — ICT {item['ict']} ({item['classe']})"
        )

    lines.extend(["", "## Evolução mensal"])
    for month in context["monthly_evolution"]:
        lines.append(
            f"- {month['competencia_str']}: ICT médio {month['ict_medio']}, "
            f"líder {month['municipio_lider']}, "
            f"{month['municipios_com_ict']} municípios com ICT"
        )

    lines.extend(["", "## Notas interpretativas"])
    for note in context["interpretation_notes"]:
        lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


def save_report_context(context: dict[str, Any], ano: int, mes: int, scope: str) -> tuple[Path, Path]:
    output_dir = report_context_dir(ano, mes)
    ensure_dir(output_dir)
    json_path = output_dir / f"ict_report_context_{scope}.json"
    md_path = output_dir / f"ict_report_context_{scope}.md"
    save_json(context, json_path)
    md_path.write_text(render_report_context_markdown(context), encoding="utf-8")
    return json_path, md_path


def _json_contains_nan(obj: Any) -> bool:
    if isinstance(obj, dict):
        return any(_json_contains_nan(value) for value in obj.values())
    if isinstance(obj, list):
        return any(_json_contains_nan(value) for value in obj)
    if isinstance(obj, float):
        return not math.isfinite(obj)
    return False


def validate_report_context(context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if _json_contains_nan(context):
        errors.append("JSON contém NaN ou infinito.")

    summary = context.get("summary", {})
    checks = {
        "municipios_total": 399,
        "municipios_com_ict": 103,
        "municipios_sem_base": 296,
    }
    for key, expected in checks.items():
        if context["metadata"].get("competencia_str") == "2026-04" and summary.get(key) != expected:
            errors.append(f"summary.{key} esperado {expected}, obtido {summary.get(key)!r}")

    top_10 = context.get("top_10", [])
    if context["metadata"].get("competencia_str") == "2026-04":
        if not top_10 or top_10[0].get("municipio") != "Curitiba":
            errors.append("top_10[0].municipio deveria ser Curitiba para 2026-04.")

    evolution = context.get("monthly_evolution", [])
    if context["metadata"].get("competencia_str") == "2026-04":
        competencias = [item.get("competencia_str") for item in evolution]
        for expected in ("2026-01", "2026-02", "2026-03", "2026-04"):
            if expected not in competencias:
                errors.append(f"monthly_evolution deveria incluir {expected}.")

    dimension_summary = context.get("dimension_summary", {})
    for column in DIMENSION_COLUMNS:
        if column not in dimension_summary:
            errors.append(f"dimension_summary ausente: {column}")

    diagnostic_flags = context.get("diagnostic_flags", {})
    for key in (
        "leaders_with_negative_quality",
        "leaders_with_negative_remuneration",
        "high_dynamism_low_quality",
        "high_complexity_low_remuneration",
    ):
        if key not in diagnostic_flags:
            errors.append(f"diagnostic_flags ausente: {key}")

    return errors


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera contexto analítico determinístico do ICT a partir da Gold."
    )
    parser.add_argument("--scope", type=str, default="pr", help="Escopo territorial (apenas pr)")
    parser.add_argument("--ano", type=int, required=True, help="Ano da competência (ex.: 2026)")
    parser.add_argument("--mes", type=int, required=True, help="Mês da competência (1-12)")
    parser.add_argument(
        "--skip-markdown",
        action="store_true",
        help="Não gravar arquivo Markdown auxiliar.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    scope = args.scope.lower().strip()

    if scope not in SUPPORTED_SCOPES:
        logger.error(SCOPE_UNSUPPORTED_MSG)
        print(SCOPE_UNSUPPORTED_MSG)
        return 1

    try:
        context = build_report_context(args.ano, args.mes, scope)
        json_path, md_path = save_report_context(context, args.ano, args.mes, scope)
        if args.skip_markdown and md_path.is_file():
            md_path.unlink()

        validation_errors = validate_report_context(context)
        if validation_errors:
            for error in validation_errors:
                logger.warning("Validação: %s", error)
                print(f"AVISO validação: {error}")
        else:
            print("Validações básicas: OK")

        summary = context["summary"]
        print(f"JSON gerado: {json_path}")
        if not args.skip_markdown:
            print(f"Markdown gerado: {md_path}")
        print(
            "Resumo | competência={competencia} | total={total} | com_ict={com_ict} | "
            "sem_base={sem_base} | ict_medio={medio} | lider={lider}".format(
                competencia=context["metadata"]["competencia_str"],
                total=summary["municipios_total"],
                com_ict=summary["municipios_com_ict"],
                sem_base=summary["municipios_sem_base"],
                medio=summary["ict_medio"],
                lider=summary["municipio_lider"],
            )
        )
        return 0
    except (FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
