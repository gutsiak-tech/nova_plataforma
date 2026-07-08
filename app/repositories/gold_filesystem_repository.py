"""Repository Gold filesystem — encapsula o comportamento atual da API."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.services.gold_service import (
    GoldMonthRef,
    Scope,
    dataframe_to_records,
    get_table_csv_path,
    read_gold_table,
)


def read_table_df(month: GoldMonthRef, *, base_name: str, scope: Scope) -> pd.DataFrame:
    return read_gold_table(month, base_name=base_name, scope=scope)


def build_table_payload(
    month: GoldMonthRef,
    *,
    base_name: str,
    scope: Scope,
    limit: int,
    offset: int,
    sort_by: str | None,
    sort_dir: str,
) -> dict[str, Any]:
    df = read_table_df(month, base_name=base_name, scope=scope)
    return {
        "month": {"ano": month.ano, "mes": month.mes},
        "scope": scope,
        "table": base_name,
        "columns": list(df.columns),
        **dataframe_to_records(
            df,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir="asc" if sort_dir == "asc" else "desc",
        ),
    }


def _top_rows(
    base_name: str,
    *,
    month: GoldMonthRef,
    scope: Scope,
    sort_by: str = "saldo",
    limit: int = 12,
) -> list[dict[str, Any]]:
    df = read_table_df(month, base_name=base_name, scope=scope)
    if sort_by not in df.columns:
        numeric_cols = [
            c
            for c in df.columns
            if c
            not in (
                "uf",
                "municipio",
                "secao",
                "cbo2002ocupacao",
                "sexo",
                "faixa_etaria",
                "graudeinstrucao",
            )
        ]
        fallback = "saldo" if "saldo" in df.columns else (numeric_cols[0] if numeric_cols else None)
        if not fallback:
            return []
        sort_by = fallback
    return dataframe_to_records(df, limit=limit, offset=0, sort_by=sort_by, sort_dir="desc")["rows"]


def _kpi_sums(df: pd.DataFrame) -> dict[str, Any]:
    for c in ("admissoes", "desligamentos", "saldo"):
        if c not in df.columns:
            raise ValueError(
                f"Coluna '{c}' ausente na tabela Gold. Colunas: {list(df.columns)}"
            )
    return {
        "admissoes": float(pd.to_numeric(df["admissoes"], errors="coerce").fillna(0).sum()),
        "desligamentos": float(
            pd.to_numeric(df["desligamentos"], errors="coerce").fillna(0).sum()
        ),
        "saldo": float(pd.to_numeric(df["saldo"], errors="coerce").fillna(0).sum()),
    }


def build_overview_payload(month: GoldMonthRef, *, scope: Scope) -> dict[str, Any]:
    resumo_row: dict[str, Any] | None = None
    if scope == "br":
        try:
            resumo = read_table_df(month, base_name="tabela_resumo", scope="br")
            resumo_row = (
                dataframe_to_records(resumo, limit=1, offset=0)["rows"][0] if len(resumo) else None
            )
        except FileNotFoundError:
            resumo_row = None

    if scope == "pr":
        uf_df = read_table_df(month, base_name="tabela_uf", scope="br")
        if "uf" not in uf_df.columns:
            raise ValueError(
                f"Coluna 'uf' ausente em tabela_uf. Colunas: {list(uf_df.columns)}"
            )
        uf_col = uf_df["uf"].astype(str)
        uf_pr = uf_df[uf_col.str.upper() == "PR"]
        if len(uf_pr) == 0:
            uf_pr = uf_df[uf_col.str.strip().str.lower() == "paraná"]
        resumo_row = (
            _kpi_sums(uf_pr)
            if len(uf_pr)
            else {"admissoes": 0.0, "desligamentos": 0.0, "saldo": 0.0}
        )

    if scope == "rmc":
        mun_rmc = read_table_df(month, base_name="tabela_municipio", scope="rmc")
        resumo_row = (
            _kpi_sums(mun_rmc)
            if len(mun_rmc)
            else {"admissoes": 0.0, "desligamentos": 0.0, "saldo": 0.0}
        )

    def _safe_top_rows(base_name: str, *, limit: int = 12) -> list[dict[str, Any]]:
        try:
            return _top_rows(base_name, month=month, scope=scope, limit=limit)
        except FileNotFoundError:
            # Propaga; routes_gold mapeia para GOLD_TABLE_NOT_FOUND.
            raise

    return {
        "month": {"ano": month.ano, "mes": month.mes},
        "scope": scope,
        "resumo": resumo_row,
        "rankings": {
            "uf": _safe_top_rows("tabela_uf", limit=12) if scope == "br" else None,
            "municipio": _safe_top_rows("tabela_municipio", limit=15),
            "setor": _safe_top_rows("tabela_setor", limit=12),
            "ocupacao": _safe_top_rows("tabela_ocupacao", limit=12),
        },
        "profiles": {
            "sexo": _safe_top_rows("tabela_perfil_sexo", limit=10),
            "faixa_etaria": _safe_top_rows("tabela_perfil_faixa_etaria", limit=20),
            "graudeinstrucao": _safe_top_rows("tabela_perfil_graudeinstrucao", limit=20),
            "sexo_faixa_etaria": _safe_top_rows("tabela_perfil_sexo_faixa_etaria", limit=24),
            "sexo_instrucao": _safe_top_rows("tabela_perfil_sexo_instrucao", limit=24),
            "faixa_etaria_instrucao": _safe_top_rows(
                "tabela_perfil_faixa_etaria_instrucao", limit=24
            ),
        },
        "salary_profiles": {
            "sexo": _safe_top_rows("tabela_perfil_sexo_salario", limit=10),
            "faixa_etaria": _safe_top_rows("tabela_perfil_faixa_etaria_salario", limit=20),
            "graudeinstrucao": _safe_top_rows("tabela_perfil_graudeinstrucao_salario", limit=20),
            "sexo_faixa_etaria": _safe_top_rows(
                "tabela_perfil_sexo_faixa_etaria_salario", limit=24
            ),
            "sexo_instrucao": _safe_top_rows("tabela_perfil_sexo_instrucao_salario", limit=24),
            "faixa_etaria_instrucao": _safe_top_rows(
                "tabela_perfil_faixa_etaria_instrucao_salario", limit=24
            ),
        },
    }


def expected_table_path(month: GoldMonthRef, *, base_name: str, scope: Scope):
    return get_table_csv_path(month, base_name=base_name, scope=scope)
