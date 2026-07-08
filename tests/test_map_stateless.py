"""Testes do padrão stateless do mapa PostGIS (sem estado global compartilhado)."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.db.queries import MAP_MUNICIPIOS_QUERY, fetch_map_municipios

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = PROJECT_ROOT / "sql"


def test_map_query_is_parameterized_by_competencia_and_uf() -> None:
    assert "WHERE ano = %s" in MAP_MUNICIPIOS_QUERY
    assert "mes = %s" in MAP_MUNICIPIOS_QUERY
    assert "uf = %s" in MAP_MUNICIPIOS_QUERY
    assert "REFRESH MATERIALIZED VIEW" not in MAP_MUNICIPIOS_QUERY.upper()


def test_no_global_map_state_sql_in_views() -> None:
    views = (SQL_DIR / "views.sql").read_text(encoding="utf-8").upper()
    assert "REFRESH MATERIALIZED VIEW" not in views
    assert "COMPETENCIA_ATIVA" not in views
    assert "INTERNAL." not in views


def test_materialized_views_file_is_deprecated_legacy_only() -> None:
    text = (SQL_DIR / "materialized_views.sql").read_text(encoding="utf-8")
    assert "LEGADO" in text
    assert "CREATE MATERIALIZED VIEW" not in text.upper()


def test_schema_uses_natural_primary_key_on_facts() -> None:
    schema = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    assert "pk_fact_emprego_municipio_mes" in schema
    assert "PRIMARY KEY (ano, mes, uf, municipio)" in schema


def test_concurrent_map_queries_use_independent_parameters() -> None:
    """Duas competências consultadas em paralelo não compartilham parâmetros."""
    calls: list[tuple] = []

    def fake_get_connection():
        conn = MagicMock()
        cur = MagicMock()

        def execute(query, params):
            calls.append(tuple(params))

        cur.execute = execute
        cur.description = [
            ("cod_municipio",),
            ("municipio",),
            ("nome_municipio",),
            ("uf",),
            ("ano",),
            ("mes",),
            ("admissoes",),
            ("desligamentos",),
            ("saldo",),
        ]
        cur.fetchall.return_value = []
        conn.cursor.return_value = cur
        return conn

    with patch("app.db.queries.get_connection", side_effect=fake_get_connection):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(fetch_map_municipios, 2026, 4, "PR")
            f2 = pool.submit(fetch_map_municipios, 2026, 3, "SP")
            f1.result()
            f2.result()

    assert (2026, 4, "PR") in calls
    assert (2026, 3, "SP") in calls
    assert len(calls) == 2


def test_map_api_route_is_get_only_stateless() -> None:
    from app.api.routes_map import municipios

    assert municipios.__name__ == "municipios"
