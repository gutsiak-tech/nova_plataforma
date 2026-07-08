"""Consultas PostGIS para o mapa — stateless (filtros por parâmetro de request)."""

from __future__ import annotations

from typing import Any

from app.db.connection import get_connection

MAP_MUNICIPIOS_QUERY = """
    SELECT
        cod_municipio,
        municipio,
        nome_municipio,
        uf,
        ano,
        mes,
        admissoes,
        desligamentos,
        saldo
    FROM serving.vw_emprego_municipio_mes
    WHERE ano = %s
      AND mes = %s
      AND uf = %s
    ORDER BY municipio;
"""


def fetch_map_municipios(ano: int, mes: int, uf: str) -> list[dict[str, Any]]:
    """Retorna métricas municipais filtradas por competência e UF.

    Não altera estado global no banco; cada chamada é independente.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(MAP_MUNICIPIOS_QUERY, (ano, mes, uf.upper()))
        rows = cur.fetchall()
        colunas = [desc[0] for desc in cur.description]
        return [dict(zip(colunas, row)) for row in rows]
    finally:
        cur.close()
        conn.close()


def ping_database() -> str:
    """Ping interno para rotas de debug autenticadas."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1")
        row = cur.fetchone()
        return "ok" if row and row[0] == 1 else "unexpected"
    finally:
        cur.close()
        conn.close()
