"""Testes estáticos de idempotência dos loaders PostGIS."""

from __future__ import annotations

from pathlib import Path

from pipelines.gold.load_fact_tables import UPSERT_FACT_SQL
from pipelines.gold.load_geo_tables import UPSERT_GEO_SQL

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_fact_loader_uses_upsert_on_conflict() -> None:
    assert "ON CONFLICT (ano, mes, uf, municipio) DO UPDATE" in UPSERT_FACT_SQL


def test_geo_loader_uses_upsert_on_conflict() -> None:
    assert "ON CONFLICT (cod_municipio) DO UPDATE" in UPSERT_GEO_SQL


def test_fact_loader_sql_does_not_use_blind_insert_only() -> None:
    assert UPSERT_FACT_SQL.strip().upper().startswith("INSERT")
    assert "DO UPDATE" in UPSERT_FACT_SQL


def test_schema_defines_fact_primary_key() -> None:
    schema = (PROJECT_ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    assert "PRIMARY KEY (ano, mes, uf, municipio)" in schema


def test_geo_table_primary_key_on_cod_municipio() -> None:
    schema = (PROJECT_ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
    assert "cod_municipio VARCHAR(7) PRIMARY KEY" in schema


def test_diagnostics_sql_includes_duplicate_checks() -> None:
    diag = (PROJECT_ROOT / "sql" / "diagnostics.sql").read_text(encoding="utf-8")
    assert "HAVING COUNT(*) > 1" in diag
