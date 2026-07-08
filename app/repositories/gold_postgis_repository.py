"""Repository Gold PostGIS — leituras territoriais migradas nesta etapa.

Não faz fallback silencioso: erros controlados sobem para o orquestrador.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.config import API_LOG_FILE
from app.core.logging import setup_logger
from app.db.connection import get_connection
from app.repositories import gold_filesystem_repository as fs_repo
from app.services.gold_service import (
    GoldMonthRef,
    Scope,
    dataframe_to_records,
    read_gold_table,
)

logger = setup_logger("api.gold.postgis", API_LOG_FILE)

# Tabelas migradas: territoriais + ICTT municipal PR.
POSTGIS_TABLE_SUPPORT: frozenset[tuple[str, Scope]] = frozenset(
    {
        ("tabela_municipio", "pr"),
        ("tabela_municipio", "rmc"),
        ("tabela_uf", "br"),
        ("tabela_ictt_municipio", "pr"),
    }
)

# Colunas do contrato Gold filesystem (exclui created_at/updated_at do PostGIS).
ICTT_PR_COLUMNS: tuple[str, ...] = (
    "ano",
    "mes",
    "competencia_str",
    "uf",
    "municipio",
    "municipio_norm",
    "status_calculo",
    "ICTT",
    "ranking_ictt",
    "percentil_ictt",
    "classe_ictt",
    "tooltip_resumo",
    "dim_dinamismo",
    "dim_remuneracao",
    "dim_qualidade_emprego",
    "dim_perfil_trabalhador",
    "dim_complexidade",
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
    "cod_municipio",
)

POSTGIS_OVERVIEW_SUPPORT: frozenset[Scope] = frozenset({"pr", "rmc", "br"})


class PostgisUnavailableError(RuntimeError):
    """PostGIS indisponível ou consulta sem dados utilizáveis."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def is_table_supported(base_name: str, scope: Scope) -> bool:
    return (base_name, scope) in POSTGIS_TABLE_SUPPORT


def is_overview_supported(scope: Scope) -> bool:
    return scope in POSTGIS_OVERVIEW_SUPPORT


def _fetch_all(sql: str, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
    try:
        conn = get_connection()
    except Exception as exc:  # noqa: BLE001 — orquestrador decide fallback
        raise PostgisUnavailableError(f"conexao: {exc}") from exc
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        return list(cur.fetchall())
    except Exception as exc:  # noqa: BLE001
        raise PostgisUnavailableError(f"query: {exc}") from exc
    finally:
        cur.close()
        conn.close()


def _fetch_dataframe(sql: str, params: tuple[Any, ...]) -> pd.DataFrame:
    try:
        conn = get_connection()
    except Exception as exc:  # noqa: BLE001
        raise PostgisUnavailableError(f"conexao: {exc}") from exc
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
        colnames = [d[0] for d in cur.description] if cur.description else []
        return pd.DataFrame.from_records(rows, columns=colnames)
    except Exception as exc:  # noqa: BLE001
        raise PostgisUnavailableError(f"query: {exc}") from exc
    finally:
        cur.close()
        conn.close()


def _gold_codigos_municipio(month: GoldMonthRef, scope: Scope) -> list[str]:
    """Lista cod_municipio da Gold da competência (exclui IGNORADO).

    Necessário enquanto o volume PostGIS puder conter resíduos de malha
    completa de loads legados (sem TRUNCATE nesta etapa).
    """
    try:
        df = read_gold_table(month, base_name="tabela_municipio", scope=scope)
    except FileNotFoundError as exc:
        raise PostgisUnavailableError(
            f"gold_codes_ausente: tabela_municipio scope={scope}"
        ) from exc
    if "cod_municipio" not in df.columns:
        raise PostgisUnavailableError("gold_sem_cod_municipio")

    codes: list[str] = []
    for _, row in df.iterrows():
        mun = str(row.get("municipio") or "").strip().upper()
        if mun in {"IGNORADO", "NAO IDENTIFICADO", "NÃO IDENTIFICADO", "NI"}:
            continue
        raw = row.get("cod_municipio")
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        text = str(raw).strip()
        if not text or text.lower() in {"nan", "none"}:
            continue
        if text.isdigit():
            text = text.zfill(7)
        codes.append(text)
    # únicos preservando ordem
    seen: set[str] = set()
    unique: list[str] = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    if not unique:
        raise PostgisUnavailableError(f"gold_codes_vazio: scope={scope}")
    return unique


def _rows_to_municipio_df(rows: list[tuple[Any, ...]]) -> pd.DataFrame:
    # uf_nome, municipio, admissoes, desligamentos, saldo, cod_municipio
    records = []
    for uf_nome, municipio, adm, des, saldo, cod in rows:
        records.append(
            {
                "uf": uf_nome,
                "municipio": municipio,
                "admissoes": int(adm) if adm is not None else 0,
                "desligamentos": int(des) if des is not None else 0,
                "saldo": int(saldo) if saldo is not None else 0,
                "cod_municipio": str(cod) if cod is not None else None,
            }
        )
    return pd.DataFrame.from_records(
        records,
        columns=["uf", "municipio", "admissoes", "desligamentos", "saldo", "cod_municipio"],
    )


def _load_municipio_df(month: GoldMonthRef, scope: Scope) -> pd.DataFrame:
    if scope not in ("pr", "rmc"):
        raise PostgisUnavailableError(f"scope_municipio_nao_suportado: {scope}")

    codes = _gold_codigos_municipio(month, scope)
    rows = _fetch_all(
        """
        SELECT COALESCE(NULLIF(BTRIM(g.nome_uf), ''), f.uf) AS uf_nome,
               f.municipio,
               f.admissoes,
               f.desligamentos,
               f.saldo,
               f.cod_municipio
        FROM serving.fact_emprego_municipio_mes f
        LEFT JOIN geo.ufs g ON g.uf = f.uf
        WHERE f.ano = %s
          AND f.mes = %s
          AND f.cod_municipio = ANY(%s)
        ORDER BY f.saldo DESC NULLS LAST, f.municipio ASC
        """,
        (month.ano, month.mes, codes),
    )
    if not rows:
        raise PostgisUnavailableError(
            f"sem_dados: fact_emprego_municipio_mes ano={month.ano} mes={month.mes} scope={scope}"
        )
    return _rows_to_municipio_df(rows)


def _load_uf_df(month: GoldMonthRef) -> pd.DataFrame:
    rows = _fetch_all(
        """
        SELECT COALESCE(NULLIF(BTRIM(f.uf_nome), ''), u.nome_uf, f.uf) AS uf_nome,
               f.admissoes,
               f.desligamentos,
               f.saldo
        FROM serving.fact_emprego_uf_mes f
        LEFT JOIN geo.ufs u ON u.uf = f.uf
        WHERE f.ano = %s
          AND f.mes = %s
          AND f.uf IS NOT NULL
          AND BTRIM(f.uf) <> ''
          AND UPPER(BTRIM(f.uf)) NOT IN ('NI', 'NA')
        ORDER BY f.saldo DESC NULLS LAST, uf_nome ASC
        """,
        (month.ano, month.mes),
    )
    if not rows:
        raise PostgisUnavailableError(
            f"sem_dados: fact_emprego_uf_mes ano={month.ano} mes={month.mes}"
        )
    records = [
        {
            "uf": uf_nome,
            "admissoes": int(adm) if adm is not None else 0,
            "desligamentos": int(des) if des is not None else 0,
            "saldo": int(saldo) if saldo is not None else 0,
        }
        for uf_nome, adm, des, saldo in rows
    ]
    return pd.DataFrame.from_records(
        records, columns=["uf", "admissoes", "desligamentos", "saldo"]
    )


def _load_ictt_pr_df(month: GoldMonthRef) -> pd.DataFrame:
    """Lê ICTT municipal PR. Coluna de índice: \"ICTT\" (mesmo nome da Gold)."""
    select_list = ", ".join(
        f'"{c}"' if c == "ICTT" else c for c in ICTT_PR_COLUMNS
    )
    df = _fetch_dataframe(
        f"""
        SELECT {select_list}
        FROM serving.fact_ictt_municipio_pr_mes
        WHERE ano = %s
          AND mes = %s
          AND cod_municipio IS NOT NULL
        ORDER BY "ICTT" DESC NULLS LAST, municipio ASC
        """,
        (month.ano, month.mes),
    )
    if df.empty:
        raise PostgisUnavailableError(
            f"sem_dados: fact_ictt_municipio_pr_mes ano={month.ano} mes={month.mes}"
        )
    # Garante ordem/contrato alinhado ao filesystem (cod_municipio aditivo ok).
    missing = [c for c in ICTT_PR_COLUMNS if c not in df.columns]
    if missing:
        raise PostgisUnavailableError(f"ictt_colunas_ausentes: {missing}")
    return df.loc[:, list(ICTT_PR_COLUMNS)]


def fetch_ictt_pr_dataframe(*, ano: int, mes: int) -> pd.DataFrame:
    """API pública para report-context / consumers PostGIS ICTT PR."""
    return _load_ictt_pr_df(GoldMonthRef(ano=ano, mes=mes))


def list_ictt_pr_competencias_upto(*, ano_max: int, mes_max: int) -> list[tuple[int, int]]:
    """Lista competências com ICTT no PostGIS até (ano_max, mes_max), ordenadas."""
    rows = _fetch_all(
        """
        SELECT DISTINCT ano, mes
        FROM serving.fact_ictt_municipio_pr_mes
        WHERE (ano < %s) OR (ano = %s AND mes <= %s)
        ORDER BY ano ASC, mes ASC
        """,
        (ano_max, ano_max, mes_max),
    )
    return [(int(ano), int(mes)) for ano, mes in rows]


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
    if not is_table_supported(base_name, scope):
        raise PostgisUnavailableError(
            f"nao_suportado: table={base_name} scope={scope}"
        )

    if base_name == "tabela_municipio":
        df = _load_municipio_df(month, scope)
    elif base_name == "tabela_uf" and scope == "br":
        df = _load_uf_df(month)
    elif base_name == "tabela_ictt_municipio" and scope == "pr":
        df = _load_ictt_pr_df(month)
    else:
        raise PostgisUnavailableError(
            f"nao_suportado: table={base_name} scope={scope}"
        )

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


def _kpi_sums(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "admissoes": float(pd.to_numeric(df["admissoes"], errors="coerce").fillna(0).sum()),
        "desligamentos": float(
            pd.to_numeric(df["desligamentos"], errors="coerce").fillna(0).sum()
        ),
        "saldo": float(pd.to_numeric(df["saldo"], errors="coerce").fillna(0).sum()),
    }


def _top_from_df(
    df: pd.DataFrame, *, limit: int, sort_by: str = "saldo"
) -> list[dict[str, Any]]:
    if df.empty:
        return []
    col = sort_by if sort_by in df.columns else ("saldo" if "saldo" in df.columns else None)
    if col is None:
        return dataframe_to_records(df, limit=limit, offset=0)["rows"]
    return dataframe_to_records(df, limit=limit, offset=0, sort_by=col, sort_dir="desc")["rows"]


def build_overview_payload(month: GoldMonthRef, *, scope: Scope) -> dict[str, Any]:
    """Overview híbrido: KPIs/rankings territoriais via PostGIS; demais blocos via filesystem."""
    if not is_overview_supported(scope):
        raise PostgisUnavailableError(f"overview_nao_suportado: scope={scope}")

    # Blocos não migrados (setor, perfil, salário) continuam no filesystem.
    # Se filesystem falhar (tabela ausente), deixa subir FileNotFoundError.
    fs_payload = fs_repo.build_overview_payload(month, scope=scope)

    if scope == "br":
        uf_df = _load_uf_df(month)
        # resumo BR (tabela_resumo) e ranking municipal BR continuam filesystem
        # (ainda sem fatos municipais Brasil no PostGIS desta etapa).
        fs_payload["rankings"]["uf"] = _top_from_df(uf_df, limit=12)
        return fs_payload

    if scope == "pr":
        uf_df = _load_uf_df(month)
        uf_pr = uf_df[uf_df["uf"].astype(str).str.strip().str.lower() == "paraná"]
        if len(uf_pr) == 0:
            uf_pr = uf_df[uf_df["uf"].astype(str).str.upper() == "PR"]
        fs_payload["resumo"] = (
            _kpi_sums(uf_pr)
            if len(uf_pr)
            else {"admissoes": 0.0, "desligamentos": 0.0, "saldo": 0.0}
        )
        mun_df = _load_municipio_df(month, "pr")
        fs_payload["rankings"]["municipio"] = _top_from_df(mun_df, limit=15)
        fs_payload["rankings"]["uf"] = None
        return fs_payload

    # rmc
    mun_rmc = _load_municipio_df(month, "rmc")
    fs_payload["resumo"] = _kpi_sums(mun_rmc)
    fs_payload["rankings"]["municipio"] = _top_from_df(mun_rmc, limit=15)
    fs_payload["rankings"]["uf"] = None
    return fs_payload
