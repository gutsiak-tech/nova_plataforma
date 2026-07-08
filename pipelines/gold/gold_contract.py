"""Contrato Silver → Gold: entradas, tabelas e artefatos esperados."""

from __future__ import annotations

SILVER_INPUT_FILE = "caged_tratado.parquet"
SILVER_METADATA_FILE = "metadata.json"
GOLD_METADATA_FILE = "metadata.json"

# Pelo menos uma coluna de competência deve existir na Silver.
COMPETENCIA_COLUMNS: tuple[str, ...] = ("competenciamov", "competencia_date")

# Colunas mínimas usadas por aggregate_indicators.py.
REQUIRED_SILVER_COLUMNS: tuple[str, ...] = (
    "saldomovimentacao",
    "admissao",
    "desligamento",
    "uf",
    "municipio",
    "secao",
    "cbo2002ocupacao",
    "sexo",
    "faixa_etaria",
    "graudeinstrucao",
    "salario",
    "valorsalariofixo",
)

# Dimensões migrantes adicionais na Silver (base filtrada; racacor mapeada no pipeline).
MIGRANT_DIMENSION_SILVER_COLUMNS: tuple[str, ...] = (
    "pais",
    "continente",
    "racacor",
)

# Tabelas Gold mínimas para operação institucional e API.
MIN_REQUIRED_GOLD_TABLES: tuple[str, ...] = (
    "tabela_resumo",
    "tabela_uf",
    "tabela_municipio",
    "tabela_setor",
    "tabela_ocupacao",
    "tabela_municipio_pr",
    "tabela_setor_pr",
    "tabela_ocupacao_pr",
    "tabela_municipio_rmc",
    "tabela_setor_rmc",
    "tabela_ocupacao_rmc",
)

# Tabelas Gold de movimentação por dimensão migrante (não salariais).
# Geradas pelo pipeline atual; não fazem parte de MIN_REQUIRED_GOLD_TABLES.
MIGRANT_MOVEMENT_GOLD_BASE_NAMES: tuple[str, ...] = (
    "tabela_pais",
    "tabela_continente",
    "tabela_perfil_racacor",
)

MIGRANT_MOVEMENT_GOLD_TABLES: tuple[str, ...] = (
    "tabela_pais",
    "tabela_pais_pr",
    "tabela_pais_rmc",
    "tabela_continente",
    "tabela_continente_pr",
    "tabela_continente_rmc",
    "tabela_perfil_racacor",
    "tabela_perfil_racacor_pr",
    "tabela_perfil_racacor_rmc",
)

MIGRANT_MOVEMENT_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "tabela_pais": ("pais", "admissoes", "desligamentos", "saldo"),
    "tabela_continente": ("continente", "admissoes", "desligamentos", "saldo"),
    "tabela_perfil_racacor": ("racacor", "admissoes", "desligamentos", "saldo"),
}

# Tabelas Gold ICTT (geradas por compute_ictt; fora de MIN_REQUIRED_GOLD_TABLES).
ICTT_GOLD_TABLES: tuple[str, ...] = (
    "tabela_ictt_municipio",
    "tabela_ictt_municipio_pr",
    "tabela_ictt_municipio_rmc",
)

# Total de nomes físicos gerados por competência (CURRENT_PIPELINE_TABLES + ICTT).
CURRENT_PIPELINE_TABLE_COUNT = 59

# Campos mínimos em tabela_resumo.csv.
TABELA_RESUMO_COLUMNS: tuple[str, ...] = (
    "admissoes",
    "desligamentos",
    "saldo",
)

# Artefatos legados que não devem existir após refatoração analítica.
LEGACY_GOLD_TABLE_NAMES: frozenset[str] = frozenset(
    {
        "tabela_perfil",
        "tabela_perfil_pr",
        "tabela_perfil_rmc",
    }
)


def excel_filename(ano: int, mes: int) -> str:
    return f"tabelas_caged_{ano}_{mes:02d}.xlsx"
