"""Testes unitários do preparador Bronze para base migrante (sem data-lake real)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from pipelines.bronze.prepare_migrantes_bronze import (
    PREPARED_REQUIRED_COLUMNS,
    PrepareMigrantesError,
    derive_idade_from_faixa_etaria,
    filter_by_competencia,
    prepare_migrantes_dataframe,
    rename_migrante_columns,
    run_prepare_migrantes_bronze,
    validate_prepared_columns,
)
from pipelines.silver.clean_caged import classificar_faixa_etaria


def _sample_migrante_row(**overrides) -> dict:
    base = {
        "competenciamov": "202601",
        "saldomovimentacao": 1,
        "pais": "VENEZUELA",
        "continente": "AMÉRICA DO SUL",
        "uf": 11,
        "municipio": 110004,
        "cbo2002ocupacao": 784205,
        "subclasse": 1510600,
        "secao": "C",
        "categoria": 101,
        "sexo": 3,
        "nivel_instrucao": 3,
        "salario": 2530.98,
        "faixa_etaria": "03",
        "racacor": 1,
        "faixa_horas_contrat": 7,
        "indtrabparcial": 0,
        "indtrabintermitente": 0,
        "tipomovimentacao": 97,
        "unidadesalariocodigo": 5,
        "valorsalariofixo": 2530.98,
    }
    base.update(overrides)
    return base


def _sample_dataframe(rows: list[dict] | None = None) -> pd.DataFrame:
    if rows is None:
        rows = [_sample_migrante_row()]
    return pd.DataFrame(rows)


def test_rename_migrante_columns() -> None:
    df = _sample_dataframe()
    renamed = rename_migrante_columns(df)

    assert "graudeinstrucao" in renamed.columns
    assert "horascontratuais" in renamed.columns
    assert "nivel_instrucao" not in renamed.columns
    assert "faixa_horas_contrat" not in renamed.columns


def test_derive_idade_from_faixa_etaria_codes() -> None:
    faixa = pd.Series(["01", "02", "03", "04", "05", "06", "07"])
    idade = derive_idade_from_faixa_etaria(faixa)

    assert idade.tolist() == [17, 21, 29, 39, 49, 59, 65]
    for code, years in zip(faixa, idade):
        assert classificar_faixa_etaria(years) != "Ignorado"


@pytest.mark.parametrize(
    ("faixa", "expected_idade", "expected_faixa_label"),
    [
        ("01", 17, "Até 17 anos"),
        ("02", 21, "18 a 24 anos"),
        ("07", 65, "65 anos ou mais"),
    ],
)
def test_derive_idade_matches_classificar_faixa_etaria(
    faixa: str, expected_idade: int, expected_faixa_label: str
) -> None:
    idade = derive_idade_from_faixa_etaria(pd.Series([faixa])).iloc[0]
    assert idade == expected_idade
    assert classificar_faixa_etaria(idade) == expected_faixa_label


def test_filter_by_competencia() -> None:
    df = _sample_dataframe(
        [
            _sample_migrante_row(competenciamov="202601"),
            _sample_migrante_row(competenciamov="202602"),
        ]
    )
    filtered = filter_by_competencia(df, 2026, 1)

    assert len(filtered) == 1
    assert str(filtered.iloc[0]["competenciamov"]) == "202601"


def test_validate_prepared_columns_raises_on_missing() -> None:
    df = _sample_dataframe()
    renamed = rename_migrante_columns(df)
    with pytest.raises(PrepareMigrantesError, match="Colunas obrigatórias ausentes"):
        validate_prepared_columns(renamed)


def test_prepare_migrantes_dataframe_full() -> None:
    prepared = prepare_migrantes_dataframe(_sample_dataframe())

    for col in PREPARED_REQUIRED_COLUMNS:
        assert col in prepared.columns
    assert prepared.iloc[0]["idade"] == 29
    assert "pais" in prepared.columns
    assert "continente" in prepared.columns
    assert "racacor" in prepared.columns


def test_derive_idade_from_faixa_etaria_0na() -> None:
    idade = derive_idade_from_faixa_etaria(pd.Series(["0NA"])).iloc[0]
    assert pd.isna(idade)


def test_prepare_migrantes_dataframe_unknown_faixa_raises() -> None:
    df = _sample_dataframe([_sample_migrante_row(faixa_etaria="99")])
    with pytest.raises(PrepareMigrantesError, match="faixa_etaria não mapeados"):
        prepare_migrantes_dataframe(df)


def test_dry_run_does_not_write_files(tmp_path: Path) -> None:
    source = tmp_path / "RAIS_CTPS_CAGED_2026_MOV.csv"
    source.write_text(
        "competenciamov;saldomovimentacao;pais;continente;uf;municipio;"
        "cbo2002ocupacao;subclasse;secao;categoria;sexo;nivel_instrucao;salario;"
        "faixa_etaria;racacor;faixa_horas_contrat;indtrabparcial;"
        "indtrabintermitente;tipomovimentacao;unidadesalariocodigo;valorsalariofixo\n"
        "202601;1;BR;AM;41;410690;351430;6911701;M;101;3;7;2000;02;3;5;0;0;97;5;2000\n",
        encoding="utf-8",
    )

    bronze_root = tmp_path / "bronze" / "caged"
    with patch(
        "pipelines.bronze.prepare_migrantes_bronze.BRONZE_CAGED_DIR",
        bronze_root,
    ):
        metadata = run_prepare_migrantes_bronze(
            2026,
            1,
            dry_run=True,
            source_path=source,
        )

    assert metadata["dry_run"] is True
    assert metadata["linhas_filtradas"] == 1
    assert metadata["linhas_salvas"] == 0
    assert not (bronze_root / "ano=2026" / "mes=01" / "microdados.txt").exists()
    assert not (bronze_root / "ano=2026" / "mes=01" / "migrantes_prep_metadata.json").exists()


def test_run_prepare_migrantes_bronze_writes_output(tmp_path: Path) -> None:
    source = tmp_path / "RAIS_CTPS_CAGED_2026_MOV.csv"
    source.write_text(
        "competenciamov;saldomovimentacao;pais;continente;uf;municipio;"
        "cbo2002ocupacao;subclasse;secao;categoria;sexo;nivel_instrucao;salario;"
        "faixa_etaria;racacor;faixa_horas_contrat;indtrabparcial;"
        "indtrabintermitente;tipomovimentacao;unidadesalariocodigo;valorsalariofixo\n"
        "202601;1;BR;AM;41;410690;351430;6911701;M;101;3;7;2000;02;3;5;0;0;97;5;2000\n",
        encoding="utf-8",
    )

    bronze_root = tmp_path / "bronze" / "caged"
    with patch(
        "pipelines.bronze.prepare_migrantes_bronze.BRONZE_CAGED_DIR",
        bronze_root,
    ):
        metadata = run_prepare_migrantes_bronze(
            2026,
            1,
            dry_run=False,
            source_path=source,
        )

    out_dir = bronze_root / "ano=2026" / "mes=01"
    microdados = out_dir / "microdados.txt"
    sidecar = out_dir / "migrantes_prep_metadata.json"

    assert microdados.is_file()
    assert sidecar.is_file()
    assert metadata["linhas_salvas"] == 1
    assert "graudeinstrucao" in microdados.read_text(encoding="utf-8")
    assert "horascontratuais" in microdados.read_text(encoding="utf-8")
    assert "idade" in microdados.read_text(encoding="utf-8")
