"""
Cálculo do ICTT — Índice de Competitividade Territorial do Trabalho.

Lê a camada Silver (microdados tratados) e grava tabela municipal na Gold.
Sem dependências de mapa, Moran ou LISA nesta etapa.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from app.core.config import PIPELINE_LOG_FILE, PROJECT_ROOT
from app.core.logging import setup_logger
from pipelines.common.utils import ensure_dir
from pipelines.geo.text_normalize import normalizar_texto_upper_sem_acento
from pipelines.gold.aggregate_indicators import MUNICIPIOS_RMC, gold_mes_dir, silver_mes_dir

logger = setup_logger("gold.ictt", PIPELINE_LOG_FILE)

Scope = Literal["br", "pr", "rmc"]

ESSENTIAL_COLUMNS: tuple[str, ...] = (
    "municipio",
    "uf",
    "saldomovimentacao",
    "admissao",
    "desligamento",
)

OPTIONAL_COLUMNS: tuple[str, ...] = (
    "salario",
    "valorsalariofixo",
    "idade",
    "horascontratuais",
    "indtrabparcial",
    "indtrabintermitente",
    "cbo2002ocupacao",
    "subclasse",
    "secao",
    "categoria",
    "graudeinstrucao",
    "sexo",
    "racacor",
)

INDICATOR_COLUMNS: tuple[str, ...] = (
    "n_movimentacoes",
    "admissoes",
    "desligamentos",
    "saldo",
    "salario_mediano_admissao",
    "salario_medio_admissao",
    "salario_mediano_desligamento",
    "salario_medio_desligamento",
    "gap_salarial_adm_des",
    "idade_media_admissao",
    "horas_media_admissao",
    "perc_parcial_admissao",
    "perc_intermitente_admissao",
    "n_cbo",
    "n_subclasse",
    "n_secao",
    "n_categoria",
    "shannon_cbo",
    "shannon_subclasse",
    "shannon_secao",
    "shannon_categoria",
)

DIMENSION_COLUMNS: tuple[str, ...] = (
    "dim_dinamismo",
    "dim_remuneracao",
    "dim_qualidade_emprego",
    "dim_perfil_trabalhador",
    "dim_complexidade",
)

DERIVED_ICTT_COLUMNS: tuple[str, ...] = (
    "ranking_ictt",
    "percentil_ictt",
    "classe_ictt",
)

TOOLTIP_COLUMN = "tooltip_resumo"

CLASSE_ICTT_SEM_DADOS = "Sem movimentação migratória suficiente"
CLASSE_ICTT_QUINTIS: tuple[str, ...] = (
    "Muito baixo",
    "Baixo",
    "Médio",
    "Alto",
    "Muito alto",
)

DIMENSION_SPECS: dict[str, dict[str, object]] = {
    "dim_dinamismo": {
        "variables": (
            "n_movimentacoes",
            "admissoes",
            "desligamentos",
            "saldo",
        ),
        "invert": ("desligamentos",),
    },
    "dim_remuneracao": {
        "variables": (
            "salario_mediano_admissao",
            "salario_medio_admissao",
            "salario_mediano_desligamento",
            "salario_medio_desligamento",
            "gap_salarial_adm_des",
        ),
        "invert": (),
    },
    "dim_qualidade_emprego": {
        "variables": (
            "horas_media_admissao",
            "perc_parcial_admissao",
            "perc_intermitente_admissao",
        ),
        "invert": ("perc_parcial_admissao", "perc_intermitente_admissao"),
    },
    "dim_perfil_trabalhador": {
        "variables": ("idade_media_admissao",),
        "invert": (),
    },
    "dim_complexidade": {
        "variables": (
            "n_cbo",
            "n_subclasse",
            "n_secao",
            "n_categoria",
            "shannon_cbo",
            "shannon_subclasse",
            "shannon_secao",
            "shannon_categoria",
        ),
        "invert": (),
    },
}

SCOPE_OUTPUT_STEM: dict[Scope, str] = {
    "pr": "tabela_ictt_municipio_pr",
    "rmc": "tabela_ictt_municipio_rmc",
    "br": "tabela_ictt_municipio",
}

GROUP_KEYS: tuple[str, str] = ("uf", "municipio")

GEO_PROCESSED_DIR = PROJECT_ROOT / "data-lake" / "geo" / "processed"
GEO_PUBLIC_FALLBACK_DIR = PROJECT_ROOT / "dashboard" / "public" / "geo"
SCOPE_GEO_FILENAME: dict[Scope, str] = {
    "pr": "municipios_pr.geojson",
    "rmc": "municipios_rmc.geojson",
}
EXPECTED_MUNICIPALITY_COUNT: dict[Scope, int] = {
    "pr": 399,
    "rmc": 29,
}
COUNT_ZERO_COLUMNS: tuple[str, ...] = (
    "n_movimentacoes",
    "admissoes",
    "desligamentos",
    "saldo",
    "n_cbo",
    "n_subclasse",
    "n_secao",
    "n_categoria",
)


@dataclass(frozen=True)
class IcttPaths:
    silver_parquet: Path
    gold_dir: Path
    output_stem: str


def silver_parquet_path(ano: int, mes: int) -> Path:
    return silver_mes_dir(ano, mes) / "caged_tratado.parquet"


def resolve_ictt_paths(ano: int, mes: int, scope: Scope) -> IcttPaths:
    scope_key = scope.lower().strip()  # type: ignore[assignment]
    if scope_key not in SCOPE_OUTPUT_STEM:
        raise ValueError(f"scope inválido: {scope!r}. Use: br | pr | rmc")
    return IcttPaths(
        silver_parquet=silver_parquet_path(ano, mes),
        gold_dir=gold_mes_dir(ano, mes),
        output_stem=SCOPE_OUTPUT_STEM[scope_key],  # type: ignore[index]
    )


def _valid_salary(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0)


def _is_sim(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper().eq("SIM")


def _valid_category(series: pd.Series) -> pd.Series:
    as_str = series.astype("string").str.strip()
    return as_str.where(as_str.notna() & (as_str != "") & (as_str.str.lower() != "nan"))



def group_shannon_entropy(df: pd.DataFrame, group_cols: list[str], value_col: str) -> pd.Series:
    if value_col not in df.columns:
        return pd.Series(dtype=float)

    tmp = df[group_cols + [value_col]].copy()
    tmp[value_col] = _valid_category(tmp[value_col])
    tmp = tmp.dropna(subset=[value_col])
    if tmp.empty:
        return pd.Series(dtype=float)

    counts = (
        tmp.groupby(group_cols + [value_col], dropna=False)
        .size()
        .reset_index(name="count")
    )
    n_categories = counts.groupby(group_cols)[value_col].nunique()
    terms = counts.copy()
    totals = terms.groupby(group_cols)["count"].transform("sum")
    terms["p"] = terms["count"] / totals
    terms["term"] = np.where(terms["p"] > 0, terms["p"] * np.log(terms["p"]), 0.0)
    entropy = -terms.groupby(group_cols)["term"].sum()

    entropy = entropy.reindex(n_categories.index)
    entropy = entropy.where(n_categories > 0, np.nan)
    entropy = entropy.mask(n_categories == 1, 0.0)
    return entropy


def group_nunique_valid(df: pd.DataFrame, group_cols: list[str], value_col: str) -> pd.Series:
    if value_col not in df.columns:
        return pd.Series(dtype=float)
    tmp = df[group_cols + [value_col]].copy()
    tmp[value_col] = _valid_category(tmp[value_col])
    return tmp.groupby(group_cols, dropna=False)[value_col].nunique(dropna=True)


def ensure_input_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in ESSENTIAL_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Colunas essenciais ausentes na Silver: {missing}. "
            f"Colunas disponíveis: {list(df.columns)}"
        )

    out = df.copy()
    for col in OPTIONAL_COLUMNS:
        if col not in out.columns:
            out[col] = np.nan
    return out


def filter_scope(df: pd.DataFrame, scope: Scope) -> pd.DataFrame:
    out = df.copy()
    out["uf_norm"] = out["uf"].map(normalizar_texto_upper_sem_acento)
    out["municipio_norm"] = out["municipio"].map(normalizar_texto_upper_sem_acento)

    if scope == "br":
        return out
    if scope == "pr":
        return out.loc[out["uf_norm"] == "PARANA"].copy()
    if scope == "rmc":
        return out.loc[
            (out["uf_norm"] == "PARANA") & (out["municipio_norm"].isin(MUNICIPIOS_RMC))
        ].copy()
    raise ValueError(f"scope inválido: {scope!r}")


def aggregate_municipal_indicators(df: pd.DataFrame) -> pd.DataFrame:
    group_cols = list(GROUP_KEYS)
    if df.empty:
        columns = list(GROUP_KEYS) + ["municipio_norm"] + list(INDICATOR_COLUMNS)
        return pd.DataFrame(columns=columns)

    base = (
        df.groupby(group_cols, dropna=False)
        .agg(
            municipio_norm=("municipio_norm", "first"),
            n_movimentacoes=("saldomovimentacao", "size"),
            admissoes=("admissao", "sum"),
            desligamentos=("desligamento", "sum"),
            saldo=("saldomovimentacao", "sum"),
        )
        .reset_index()
    )

    adm = df.loc[df["admissao"] == 1].copy()
    des = df.loc[df["desligamento"] == 1].copy()

    if not adm.empty:
        adm = adm.assign(
            _salario_valido=_valid_salary(adm["salario"]),
            _horas_validas=pd.to_numeric(adm["horascontratuais"], errors="coerce"),
            _idade_valida=pd.to_numeric(adm["idade"], errors="coerce"),
            _parcial=_is_sim(adm["indtrabparcial"]),
            _intermitente=_is_sim(adm["indtrabintermitente"]),
        )
        adm_agg = (
            adm.groupby(group_cols, dropna=False)
            .agg(
                salario_mediano_admissao=("_salario_valido", "median"),
                salario_medio_admissao=("_salario_valido", "mean"),
                idade_media_admissao=("_idade_valida", "mean"),
                horas_media_admissao=("_horas_validas", "mean"),
                perc_parcial_admissao=("_parcial", "mean"),
                perc_intermitente_admissao=("_intermitente", "mean"),
            )
            .reset_index()
        )
        base = base.merge(adm_agg, on=group_cols, how="left")

    if not des.empty:
        des = des.assign(_salario_valido=_valid_salary(des["salario"]))
        des_agg = (
            des.groupby(group_cols, dropna=False)
            .agg(
                salario_mediano_desligamento=("_salario_valido", "median"),
                salario_medio_desligamento=("_salario_valido", "mean"),
            )
            .reset_index()
        )
        base = base.merge(des_agg, on=group_cols, how="left")

    for col, n_col in (
        ("cbo2002ocupacao", "n_cbo"),
        ("subclasse", "n_subclasse"),
        ("secao", "n_secao"),
        ("categoria", "n_categoria"),
    ):
        nunique_df = group_nunique_valid(df, group_cols, col).rename(n_col).reset_index()
        base = base.merge(nunique_df, on=group_cols, how="left")

    for col, shannon_col in (
        ("cbo2002ocupacao", "shannon_cbo"),
        ("subclasse", "shannon_subclasse"),
        ("secao", "shannon_secao"),
        ("categoria", "shannon_categoria"),
    ):
        shannon_df = group_shannon_entropy(df, group_cols, col).rename(shannon_col).reset_index()
        base = base.merge(shannon_df, on=group_cols, how="left")

    base["gap_salarial_adm_des"] = (
        base["salario_mediano_admissao"] - base["salario_mediano_desligamento"]
    )

    for col in INDICATOR_COLUMNS:
        if col not in base.columns:
            base[col] = np.nan

    base["perc_parcial_admissao"] = base["perc_parcial_admissao"] * 100.0
    base["perc_intermitente_admissao"] = base["perc_intermitente_admissao"] * 100.0

    return base


def _useful_variables(frame: pd.DataFrame, variables: Iterable[str]) -> list[str]:
    useful: list[str] = []
    for var in variables:
        if var not in frame.columns:
            continue
        series = pd.to_numeric(frame[var], errors="coerce")
        if series.notna().sum() < 2:
            continue
        if series.nunique(dropna=True) < 2:
            continue
        useful.append(var)
    return useful


def _impute_median(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame[columns].apply(pd.to_numeric, errors="coerce").copy()
    for col in columns:
        median = out[col].median(skipna=True)
        if pd.isna(median):
            median = 0.0
        out[col] = out[col].fillna(median)
    return out


def _zscore(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    std = values.std(skipna=True)
    if std is None or pd.isna(std) or std == 0:
        return pd.Series(np.zeros(len(values)), index=series.index, dtype=float)
    return (values - values.mean(skipna=True)) / std


def _align_pca_sign(
    scores: np.ndarray,
    matrix: np.ndarray,
    reference_idx: int,
) -> np.ndarray:
    if matrix.shape[1] == 0:
        return scores
    ref = matrix[:, reference_idx]
    corr = np.corrcoef(scores, ref)[0, 1]
    if np.isfinite(corr) and corr < 0:
        return -scores
    return scores


def compute_dimension_scores(
    indicators: pd.DataFrame,
    sufficient: pd.Series,
) -> pd.DataFrame:
    out = indicators.copy()
    for dim_name in DIMENSION_COLUMNS:
        out[dim_name] = np.nan

    if not sufficient.any():
        return out

    analytic = out.loc[sufficient].copy()

    for dim_name, spec in DIMENSION_SPECS.items():
        variables = list(spec["variables"])  # type: ignore[arg-type]
        invert = set(spec.get("invert", ()))  # type: ignore[arg-type]
        useful = _useful_variables(analytic, variables)

        if not useful:
            continue

        work = _impute_median(analytic, useful).copy()
        for var in useful:
            if var in invert:
                work[var] = -work[var]

        if len(useful) == 1:
            scores = _zscore(work[useful[0]])
            out.loc[sufficient, dim_name] = scores.to_numpy()
            continue

        scaler = StandardScaler()
        scaled = scaler.fit_transform(work[useful].to_numpy(dtype=float))
        pca = PCA(n_components=1)
        scores = pca.fit_transform(scaled).ravel()

        reference_idx = 0
        for idx, var in enumerate(useful):
            if var not in invert:
                reference_idx = idx
                break
        scores = _align_pca_sign(scores, scaled, reference_idx)
        out.loc[sufficient, dim_name] = scores

    return out


def resolve_geojson_path(scope: Scope) -> Path:
    if scope not in SCOPE_GEO_FILENAME:
        raise ValueError(f"scope sem malha municipal suportada: {scope!r}")
    filename = SCOPE_GEO_FILENAME[scope]
    candidates = (
        GEO_PROCESSED_DIR / filename,
        GEO_PUBLIC_FALLBACK_DIR / filename,
    )
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError(
        f"GeoJSON municipal não encontrado para scope={scope!r}. "
        f"Procurado em: {', '.join(str(p) for p in candidates)}"
    )


def load_municipality_universe(scope: Scope) -> pd.DataFrame:
    """Malha municipal completa do escopo (universo-base para o ICTT)."""
    geo_path = resolve_geojson_path(scope)
    payload = json.loads(geo_path.read_text(encoding="utf-8"))
    features = payload.get("features") or []

    rows: list[dict[str, str]] = []
    for feature in features:
        properties = feature.get("properties") or {}
        municipio_norm = properties.get("municipio_norm")
        if municipio_norm is None or str(municipio_norm).strip() == "":
            municipio_norm = normalizar_texto_upper_sem_acento(properties.get("municipio"))
        if municipio_norm is None or str(municipio_norm).strip() == "":
            continue
        rows.append(
            {
                "uf": properties.get("uf") or "Paraná",
                "municipio": properties.get("municipio"),
                "municipio_norm": str(municipio_norm).strip(),
            }
        )

    universe = pd.DataFrame(rows).drop_duplicates(subset=["municipio_norm"], keep="first")
    universe = universe.sort_values(["municipio_norm"], kind="mergesort").reset_index(drop=True)

    expected = EXPECTED_MUNICIPALITY_COUNT.get(scope)
    if expected is not None and len(universe) != expected:
        raise ValueError(
            f"Malha municipal inesperada para scope={scope!r}: "
            f"esperado {expected}, obtido {len(universe)} ({geo_path})"
        )
    return universe


def expand_to_municipality_universe(
    aggregated: pd.DataFrame,
    universe: pd.DataFrame,
) -> pd.DataFrame:
    """Une indicadores da Silver à malha completa; municípios sem dados permanecem na tabela."""
    agg = aggregated.drop(columns=["uf", "municipio"], errors="ignore")
    agg = agg.drop_duplicates(subset=["municipio_norm"], keep="first")
    merged = universe.merge(agg, on="municipio_norm", how="left")

    for col in COUNT_ZERO_COLUMNS:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    for col in INDICATOR_COLUMNS:
        if col not in merged.columns:
            merged[col] = np.nan

    merged["gap_salarial_adm_des"] = (
        merged["salario_mediano_admissao"] - merged["salario_mediano_desligamento"]
    )

    return merged


def _has_sufficient_data(row: pd.Series) -> bool:
    """
    Regra de cobertura ICTT (base analítica para PCA e ICTT):
    - calculado: admissoes > 0 e n_movimentacoes > 0 no mês;
    - sem_dados_suficientes: caso contrário (município permanece na malha).
    """
    admissoes = pd.to_numeric(row.get("admissoes"), errors="coerce")
    n_mov = pd.to_numeric(row.get("n_movimentacoes"), errors="coerce")
    return bool(pd.notna(admissoes) and admissoes > 0 and pd.notna(n_mov) and n_mov > 0)


def compute_final_ictt(indicators: pd.DataFrame) -> pd.DataFrame:
    out = indicators.copy()
    sufficient = out.apply(_has_sufficient_data, axis=1)
    out["status_calculo"] = "sem_dados_suficientes"
    out["ICTT"] = np.nan

    dim_cols = list(DIMENSION_COLUMNS)
    useful_dims = _useful_variables(out.loc[sufficient], dim_cols)
    if not useful_dims or not sufficient.any():
        return out

    imputed = _impute_median(out.loc[sufficient], useful_dims)

    if len(useful_dims) == 1:
        raw = _zscore(imputed[useful_dims[0]])
    else:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(imputed[useful_dims].to_numpy(dtype=float))
        pca = PCA(n_components=1)
        raw = pd.Series(
            pca.fit_transform(scaled).ravel(),
            index=imputed.index,
            dtype=float,
        )
        aligned = _align_pca_sign(raw.to_numpy(), scaled, 0)
        raw = pd.Series(aligned, index=imputed.index, dtype=float)

    raw_values = raw.to_numpy(dtype=float)
    finite = np.isfinite(raw_values)
    if finite.sum() == 0:
        return out

    min_v = float(np.nanmin(raw_values[finite]))
    max_v = float(np.nanmax(raw_values[finite]))
    if np.isclose(min_v, max_v):
        scaled_scores = np.full(raw_values.shape, 50.0)
    else:
        scaled_scores = (raw_values - min_v) / (max_v - min_v) * 100.0

    out.loc[sufficient, "ICTT"] = scaled_scores
    out.loc[sufficient, "status_calculo"] = "calculado"
    return out


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "<na>"}


def _format_br_decimal(value: float, decimals: int) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    formatted = f"{absolute:.{decimals}f}"
    if decimals > 0 and "." in formatted:
        int_part, dec_part = formatted.split(".", 1)
    else:
        int_part, dec_part = formatted, ""

    grouped: list[str] = []
    while int_part:
        grouped.insert(0, int_part[-3:])
        int_part = int_part[:-3]
    int_str = ".".join(grouped) if grouped else "0"

    if decimals == 0:
        return f"{sign}{int_str}"
    return f"{sign}{int_str},{dec_part}"


def format_number(value: object, decimals: int = 1) -> str:
    """Formata número no padrão BR; ausente → '--'."""
    if _is_missing_value(value):
        return "--"
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return "--"
    if decimals == 0:
        return _format_br_decimal(float(num), 0)
    return _format_br_decimal(float(num), decimals)


def format_currency_br(value: object) -> str:
    """Formata moeda BRL; ausente → '--'."""
    if _is_missing_value(value):
        return "--"
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return "--"
    return f"R$ {_format_br_decimal(float(num), 2)}"


def _format_ranking(value: object) -> str:
    if _is_missing_value(value):
        return "--"
    num = pd.to_numeric(value, errors="coerce")
    if pd.isna(num):
        return "--"
    return f"{int(round(num))}º"


def build_tooltip_resumo(row: pd.Series) -> str:
    """Texto curto para tooltip do mapa ICTT."""
    municipio = row.get("municipio")
    if _is_missing_value(municipio):
        municipio = row.get("municipio_norm", "--")
    municipio = str(municipio).strip()

    if _is_missing_value(row.get("ICTT")):
        return (
            f"{municipio}\n"
            f"Status: {CLASSE_ICTT_SEM_DADOS}\n"
            "Não houve base suficiente de movimentação formal de migrantes nesta "
            "competência para calcular o ICTT."
        )

    classe = row.get("classe_ictt")
    classe_text = str(classe).strip() if not _is_missing_value(classe) else "--"

    lines = [
        municipio,
        (
            f"ICTT: {format_number(row.get('ICTT'), 1)} | "
            f"Classe: {classe_text} | "
            f"Ranking: {_format_ranking(row.get('ranking_ictt'))} | "
            f"Percentil: {format_number(row.get('percentil_ictt'), 1)}"
        ),
        (
            f"Admissões: {format_number(row.get('admissoes'), 0)} | "
            f"Desligamentos: {format_number(row.get('desligamentos'), 0)} | "
            f"Saldo: {format_number(row.get('saldo'), 0)}"
        ),
        f"Salário admissão: {format_currency_br(row.get('salario_mediano_admissao'))}",
        (
            "Dimensões: "
            f"Dinamismo {format_number(row.get('dim_dinamismo'), 2)} | "
            f"Remuneração {format_number(row.get('dim_remuneracao'), 2)} | "
            f"Qualidade {format_number(row.get('dim_qualidade_emprego'), 2)} | "
            f"Perfil {format_number(row.get('dim_perfil_trabalhador'), 2)} | "
            f"Complexidade {format_number(row.get('dim_complexidade'), 2)}"
        ),
        f"Shannon CBO: {format_number(row.get('shannon_cbo'), 2)}",
    ]
    return "\n".join(lines)


def add_tooltip_resumo(indicators: pd.DataFrame) -> pd.DataFrame:
    out = indicators.copy()
    out[TOOLTIP_COLUMN] = out.apply(build_tooltip_resumo, axis=1).astype(str)
    return out


def _assign_classe_ictt_empirical(ictt: pd.Series) -> tuple[pd.Series, str | None]:
    """
    Quintis empíricos (frequência ~igual) sobre ICTT válido via pd.qcut.

    Retorna (classes, nota_fallback). nota_fallback é preenchida quando o número
    efetivo de classes fica abaixo de 5 (duplicates='drop', poucos únicos, etc.).
    """
    n_valid = int(ictt.count())
    n_unique = int(ictt.nunique(dropna=True))

    if n_valid == 0:
        return pd.Series(dtype=object), None

    if n_unique == 1:
        return (
            pd.Series(CLASSE_ICTT_QUINTIS[2], index=ictt.index, dtype=object),
            "valor_unico: todos recebem classe Médio",
        )

    for q in (5, 4, 3, 2):
        if q > n_valid:
            continue
        try:
            _, bin_edges = pd.qcut(ictt, q=q, retbins=True, duplicates="drop")
            n_bins = len(bin_edges) - 1
            if n_bins < 1:
                continue
            labels = list(CLASSE_ICTT_QUINTIS[:n_bins])
            classes = pd.qcut(ictt, q=q, labels=labels, duplicates="drop")
            note: str | None = None
            if n_bins < 5 or q < 5:
                note = (
                    f"fallback qcut: q_solicitado={q}, bins_efetivos={n_bins}, "
                    f"validos={n_valid}, unicos={n_unique}"
                )
                logger.info("classe_ictt | %s", note)
            return classes.astype(str), note
        except ValueError:
            continue

    n_groups = min(5, n_valid, max(n_unique, 1))
    ranks = ictt.rank(method="first")
    groups = pd.cut(
        ranks,
        bins=n_groups,
        labels=list(CLASSE_ICTT_QUINTIS[:n_groups]),
        include_lowest=True,
    )
    note = (
        f"fallback rank-based: grupos={n_groups}, validos={n_valid}, unicos={n_unique}"
    )
    logger.info("classe_ictt | %s", note)
    return groups.astype(str), note


def compute_ictt_derivatives(indicators: pd.DataFrame) -> pd.DataFrame:
    """
    Deriva ranking, percentil e classe a partir do ICTT já calculado.

    ranking_ictt: método ``dense`` (pandas), ordem decrescente — maior ICTT = 1;
    empates recebem o mesmo ranking; NaN permanece NaN.

    percentil_ictt: escala 0–100 por min-max entre municípios com ICTT válido;
    valor único → 50,0 para todos os válidos.

    classe_ictt: quintis empíricos (pd.qcut) sobre ICTT válido; sem ICTT →
    CLASSE_ICTT_SEM_DADOS.
    """
    out = indicators.copy()
    out["ranking_ictt"] = np.nan
    out["percentil_ictt"] = np.nan
    out["classe_ictt"] = CLASSE_ICTT_SEM_DADOS

    valid = out["ICTT"].notna()
    if not valid.any():
        return out

    ictt = pd.to_numeric(out.loc[valid, "ICTT"], errors="coerce")

    # dense: maior ICTT → ranking 1; empates compartilham posição
    out.loc[valid, "ranking_ictt"] = ictt.rank(method="dense", ascending=False)

    min_v = float(ictt.min())
    max_v = float(ictt.max())
    if np.isclose(min_v, max_v):
        out.loc[valid, "percentil_ictt"] = 50.0
    else:
        out.loc[valid, "percentil_ictt"] = (ictt - min_v) / (max_v - min_v) * 100.0

    classes, _ = _assign_classe_ictt_empirical(ictt)
    out.loc[valid, "classe_ictt"] = classes

    return out


def validate_ictt_output(result: pd.DataFrame, scope: Scope) -> None:
    if result.empty:
        raise ValueError("Tabela ICTT vazia após expansão para a malha municipal.")

    if result["municipio_norm"].isna().any() or (result["municipio_norm"].astype(str).str.strip() == "").any():
        raise ValueError("municipio_norm ausente na tabela ICTT final.")

    if result["status_calculo"].isna().any() or (result["status_calculo"].astype(str).str.strip() == "").any():
        raise ValueError("status_calculo ausente na tabela ICTT final.")

    if result["municipio_norm"].duplicated().any():
        duplicated = result.loc[result["municipio_norm"].duplicated(), "municipio_norm"].tolist()
        raise ValueError(f"municipio_norm duplicado na tabela ICTT: {duplicated[:5]}")

    expected = EXPECTED_MUNICIPALITY_COUNT.get(scope)
    if expected is not None and len(result) != expected:
        raise ValueError(
            f"Tabela ICTT com {len(result)} linhas; esperado {expected} para scope={scope!r}."
        )

    if TOOLTIP_COLUMN not in result.columns:
        raise ValueError(f"Coluna ausente na tabela ICTT final: {TOOLTIP_COLUMN}")

    empty_tooltip = result[TOOLTIP_COLUMN].isna() | (result[TOOLTIP_COLUMN].astype(str).str.strip() == "")
    if empty_tooltip.any():
        raise ValueError("tooltip_resumo vazio em pelo menos um município.")


def print_ictt_summary(result: pd.DataFrame) -> None:
    status_counts = result["status_calculo"].value_counts(dropna=False).to_dict()
    ictt_not_null = int(result["ICTT"].notna().sum())
    ictt_null = int(result["ICTT"].isna().sum())

    print(f"\nTotal de linhas: {len(result)}")
    print("status_calculo:")
    for key, value in status_counts.items():
        print(f"  {key}: {value}")
    print(f"Municípios com ICTT não nulo: {ictt_not_null}")
    print(f"Municípios com ICTT nulo: {ictt_null}")

    if "classe_ictt" in result.columns:
        print("classe_ictt:")
        for key, value in result["classe_ictt"].value_counts(dropna=False).items():
            print(f"  {key}: {value}")

    if "ranking_ictt" in result.columns:
        top_cols = ["municipio", "ICTT", "ranking_ictt", "percentil_ictt", "classe_ictt"]
        top = (
            result.loc[result["ranking_ictt"].notna(), top_cols]
            .sort_values("ranking_ictt", kind="mergesort")
            .head(10)
        )
        print("\nTop 10 ranking_ictt:")
        print(top.to_string(index=False) if not top.empty else "  (nenhum)")

    sample_cols = ["municipio", "municipio_norm", "status_calculo", "ICTT", "admissoes", "n_movimentacoes"]
    insufficient = result.loc[result["status_calculo"] == "sem_dados_suficientes", sample_cols].head(5)
    calculated = result.loc[result["status_calculo"] == "calculado", sample_cols].head(5)

    print("\nAmostra — sem_dados_suficientes:")
    print(insufficient.to_string(index=False) if not insufficient.empty else "  (nenhum)")
    print("\nAmostra — calculado:")
    print(calculated.to_string(index=False) if not calculated.empty else "  (nenhum)")


def build_output_table(indicators: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    output_columns = [
        "ano",
        "mes",
        "competencia_str",
        "uf",
        "municipio",
        "municipio_norm",
        "status_calculo",
        "ICTT",
        *DERIVED_ICTT_COLUMNS,
        TOOLTIP_COLUMN,
        *DIMENSION_COLUMNS,
        *INDICATOR_COLUMNS,
    ]
    out = indicators.copy()
    out["ano"] = int(ano)
    out["mes"] = int(mes)
    out["competencia_str"] = f"{ano}-{mes:02d}"
    for col in output_columns:
        if col not in out.columns:
            out[col] = np.nan
    out = out[output_columns]
    out = out.sort_values(["uf", "municipio"], kind="mergesort").reset_index(drop=True)
    return out


def save_ictt_table(df: pd.DataFrame, gold_dir: Path, output_stem: str) -> tuple[Path, Path]:
    ensure_dir(gold_dir)
    parquet_path = gold_dir / f"{output_stem}.parquet"
    csv_path = gold_dir / f"{output_stem}.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return parquet_path, csv_path


def compute_ictt(ano: int, mes: int, scope: str = "pr") -> pd.DataFrame:
    scope_key = scope.lower().strip()
    if scope_key not in SCOPE_OUTPUT_STEM:
        raise ValueError(f"scope inválido: {scope!r}. Use: br | pr | rmc")

    paths = resolve_ictt_paths(ano, mes, scope_key)  # type: ignore[arg-type]
    if not paths.silver_parquet.is_file():
        raise FileNotFoundError(
            f"Silver não encontrada: {paths.silver_parquet}. "
            "Execute o pipeline Silver antes do ICTT."
        )

    logger.info(
        "Iniciando ICTT | ano=%s | mes=%02d | scope=%s | silver=%s",
        ano,
        mes,
        scope_key,
        paths.silver_parquet,
    )

    silver = pd.read_parquet(paths.silver_parquet)
    silver = ensure_input_columns(silver)
    scoped = filter_scope(silver, scope_key)  # type: ignore[arg-type]

    indicators = aggregate_municipal_indicators(scoped)
    universe = load_municipality_universe(scope_key)  # type: ignore[arg-type]
    indicators = expand_to_municipality_universe(indicators, universe)

    sufficient = indicators.apply(_has_sufficient_data, axis=1)
    indicators = compute_dimension_scores(indicators, sufficient)
    indicators = compute_final_ictt(indicators)
    indicators = compute_ictt_derivatives(indicators)
    indicators = add_tooltip_resumo(indicators)
    result = build_output_table(indicators, ano=ano, mes=mes)

    validate_ictt_output(result, scope_key)  # type: ignore[arg-type]

    parquet_path, csv_path = save_ictt_table(result, paths.gold_dir, paths.output_stem)
    logger.info(
        "ICTT salvo | linhas=%s | parquet=%s | csv=%s",
        len(result),
        parquet_path,
        csv_path,
    )
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calcula ICTT municipal na camada Gold.")
    parser.add_argument("--ano", type=int, required=True, help="Ano da competência (ex.: 2026)")
    parser.add_argument("--mes", type=int, required=True, help="Mês da competência (1-12)")
    parser.add_argument(
        "--scope",
        type=str,
        default="pr",
        choices=sorted(SCOPE_OUTPUT_STEM.keys()),
        help="Recorte territorial (default: pr)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not (1 <= args.mes <= 12):
        raise SystemExit("mes inválido: use um valor entre 1 e 12.")

    result = compute_ictt(ano=args.ano, mes=args.mes, scope=args.scope)
    print_ictt_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
